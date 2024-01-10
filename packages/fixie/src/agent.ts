/**
 * @fileoverview This module provides a NodeJS interface to the Fixie
 * Agent API, as well as utilities for deploying and serving Fixie Agents.
 */

import { FixieAgentBase, Agent, AgentRevision, AgentId } from '@fixieai/fixie-common';
import { FixieClient } from './client.js';
import yaml from 'js-yaml';
import fs from 'fs';
import terminal from 'terminal-kit';
import { execSync } from 'child_process';
import ora from 'ora';
import os from 'os';
import path from 'path';
import { execa } from 'execa';
import Watcher from 'watcher';
import net from 'node:net';
import * as TJS from 'typescript-json-schema';
import _ from 'lodash';

const { terminal: term } = terminal;

/** Represents the contents of an agent.yaml configuration file. */
export interface AgentConfig {
  handle: string;
  name?: string;
  description?: string;
  moreInfoUrl?: string;
  deploymentUrl?: string;
}

/**
 * This class provides an interface to the Fixie Agent API for NodeJS clients.
 */
export class FixieAgent extends FixieAgentBase {
  /** Use GetAgent or CreateAgent instead of calling this constructor. */
  protected constructor(protected readonly client: FixieClient, protected agentMetadata: Agent) {
    super(client, agentMetadata);
  }

  /** Get the agent with the given ID. */
  public static async GetAgent({ client, agentId }: { client: FixieClient; agentId: AgentId }): Promise<FixieAgent> {
    const metadata = await FixieAgentBase.getAgentById(client, agentId);
    return new FixieAgent(client, metadata);
  }

  /** Load an agent configuration from the given directory. */
  public static LoadConfig(agentPath: string): AgentConfig {
    const fullPath = path.resolve(path.join(agentPath, 'agent.yaml'));
    const rawConfig = yaml.load(fs.readFileSync(fullPath, 'utf8')) as Partial<AgentConfig>;
    const config: Partial<AgentConfig> = {};
    Object.keys(rawConfig).forEach((key: string) => {
      config[_.camelCase(key) as keyof Partial<AgentConfig>] = rawConfig[key as keyof Partial<AgentConfig>];
    });

    // Warn if any fields are present in config that are not supported.
    const validKeys = ['handle', 'name', 'description', 'moreInfoUrl', 'deploymentUrl'];
    const invalidKeys = Object.keys(config).filter((key) => !validKeys.includes(key));
    for (const key of invalidKeys) {
      term('❓ Ignoring invalid key ').yellow(key)(' in agent.yaml\n');
    }
    return config as AgentConfig;
  }

  private static inferRuntimeParametersSchema(agentPath: string): TJS.Definition | null {
    // If there's a tsconfig.json file, try to use Typescript to produce a JSON schema
    // with the runtime parameters for the agent.
    const tsconfigPath = path.resolve(path.join(agentPath, 'tsconfig.json'));
    if (!fs.existsSync(tsconfigPath)) {
      term.yellow(`⚠️ tsconfig.json not found at ${tsconfigPath}. Your agent will not support runtime parameters.\n`);
      return null;
    }

    const settings: TJS.PartialArgs = {
      required: true,
      noExtraProps: true,
    };

    // We're currently assuming the entrypoint is exported from src/index.{ts,tsx}.
    const handlerPath = path.resolve(path.join(agentPath, 'src/index.js'));
    const tempPath = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'fixie-')), 'extract-parameters-schema.mts');
    fs.writeFileSync(
      tempPath,
      `
      import Handler from '${handlerPath}';
      export type RuntimeParameters = Parameters<typeof Handler> extends [infer T, ...any] ? T : {};
      `
    );
    const program = TJS.programFromConfig(tsconfigPath, [tempPath]);
    const schema = TJS.generateSchema(program, 'RuntimeParameters', settings);
    if (schema && schema.type !== 'object') {
      throw new Error(`The first argument of your default export must be an object (not ${schema.type})`);
    }

    return schema;
  }

  /** Package the code in the given directory and return the path to the tarball. */
  private static getCodePackage(agentPath: string): string {
    // Read the package.json file to get the package name and version.
    const packageJsonPath = path.resolve(path.join(agentPath, 'package.json'));
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));

    // Create a temporary directory and run `npm pack` inside.
    const tempdir = fs.mkdtempSync(path.join(os.tmpdir(), `fixie-tmp-${packageJson.name}-${packageJson.version}-`));
    const commandline = `npm pack ${path.resolve(agentPath)}`;
    try {
      execSync(commandline, { cwd: tempdir, stdio: 'inherit' });
    } catch (ex) {
      throw new Error(`\`${commandline}\` failed. Check for build errors above and retry.`);
    }
    return `${tempdir}/${packageJson.name}-${packageJson.version}.tgz`;
  }

  /**
   * Create a new agent revision.
   *
   * @param defaultRuntimeParameters The default runtime parameters for the agent.
   * @param externalUrl The URL of the agent's external deployment, if any.
   * @param runtimeParametersSchema The JSON-encoded schema for the agent's runtime parameters.
   *   May only be specified if `externalUrl` is also specified.
   * @param isCurrent Whether this revision should be the current revision.
   * @param tarball The path to the tarball containing the agent code.
   * @param environmentVariables The environment variables to set for the agent.
   *   May only be specified if `tarball` is also specified.
   *
   * @returns The created agent revision.
   */
  public async createRevision({
    defaultRuntimeParameters,
    externalUrl,
    runtimeParametersSchema,
    tarball,
    environmentVariables,
    isCurrent = true,
  }: {
    defaultRuntimeParameters?: Record<string, unknown>;
    externalUrl?: string;
    runtimeParametersSchema?: string;
    tarball?: string;
    environmentVariables?: Record<string, string>;
    isCurrent?: boolean;
  }): Promise<AgentRevision> {
    if (externalUrl === undefined && defaultRuntimeParameters === undefined && tarball === undefined) {
      throw new Error('Must specify either externalUrl, defaultRuntimeParameters, or tarball');
    }
    if (externalUrl && (tarball || environmentVariables)) {
      throw Error('Cannot specify both externalUrl and either tarball or environmentVariables');
    }
    if (environmentVariables && !tarball) {
      throw Error('Cannot specify environmentVariables without also specifying tarball');
    }
    if (!tarball) {
      // Our base class handles this case.
      return super.createRevision({
        defaultRuntimeParameters,
        externalUrl,
        runtimeParametersSchema,
        isCurrent,
      });
    }

    const tarballData = fs.readFileSync(fs.realpathSync(tarball));
    const codePackage = tarballData.toString('base64');

    const envVars = environmentVariables
      ? Object.entries(environmentVariables).map(([key, value]) => ({ name: key, value }))
      : undefined;

    const result = (await this.client.requestJson(`/api/v1/agents/${this.metadata.agentId}/revisions`, {
      revision: {
        isCurrent,
        deployment: {
          managed: {
            codePackage,
            environmentVariables: envVars,
            runtimeParametersSchema,
          },
        },
        defaultRuntimeParameters,
      },
    })) as { revision: AgentRevision };
    return result.revision;
  }

  /** Ensure that the agent is created or updated. */
  private static async ensureAgent({
    client,
    config,
    teamId,
  }: {
    client: FixieClient;
    config: AgentConfig;
    teamId?: string;
  }): Promise<FixieAgent> {
    let agent: FixieAgentBase | null;
    // The API does not currently provide a way to return an agent by its handle, so we scan
    // to see if the agent with the same handle already exists.
    const agentList = await FixieAgentBase.ListAgents({ client, teamId });
    agent = agentList.find((agent) => agent.metadata.handle === config.handle) ?? null;
    if (agent) {
      await agent.update({
        displayName: config.name,
        description: config.description,
        moreInfoUrl: config.moreInfoUrl,
      });
    } else {
      // Try to create the agent instead.
      term('🦊 Creating new agent ').green(config.handle)('...\n');
      agent = (await FixieAgent.CreateAgent({
        client,
        handle: config.handle,
        displayName: config.name,
        description: config.description,
        moreInfoUrl: config.moreInfoUrl,
      })) as FixieAgent;
    }
    return agent as FixieAgent;
  }

  static spawnAgentProcess(agentPath: string, port: number, env: Record<string, string>) {
    term(`🌱 Building agent at ${agentPath}...\n`);
    this.getCodePackage(agentPath);

    const pathToCheck = path.resolve(path.join(agentPath, 'dist', 'index.js'));
    if (!fs.existsSync(pathToCheck)) {
      throw Error(`Your agent was not found at ${pathToCheck}. Did the build fail?`);
    }

    const cmdline = `npx --package=@fixieai/sdk fixie-serve-bin --packagePath ./dist/index.js --port ${port}`;
    // Split cmdline into the first value (argv0) and a list of arguments separated by spaces.
    term('🌱 Running: ').green(cmdline)('\n');

    const [argv0, ...args] = cmdline.split(' ');
    const subProcess = execa(argv0, args, { cwd: agentPath, env });
    term('🌱 Agent process running at PID: ').green(subProcess.pid)('\n');
    subProcess.stdout?.setEncoding('utf8');
    subProcess.stderr?.setEncoding('utf8');

    subProcess.on('spawn', () => {
      console.log(`🌱 Agent child process started with PID [${subProcess.pid}]`);
    });
    subProcess.stdout?.on('data', (sdata: string) => {
      console.log(`🌱 Agent stdout: ${sdata.trimEnd()}`);
    });
    subProcess.stderr?.on('data', (sdata: string) => {
      console.error(`🌱 Agent stdout: ${sdata.trimEnd()}`);
    });
    subProcess.on('error', (err: any) => {
      term('🌱 ').red(`Agent child process [${subProcess.pid}] exited with error: ${err.message}\n`);
    });
    subProcess.on('close', (returnCode: number) => {
      term('🌱 ').red(`Agent child process [${subProcess.pid}] exited with code ${returnCode}\n`);
    });
    return subProcess;
  }

  /** Deploy an agent from the given directory. */
  public static async DeployAgent(
    client: FixieClient,
    agentPath: string,
    environmentVariables: Record<string, string> = {}
  ): Promise<AgentRevision> {
    const config = await FixieAgent.LoadConfig(agentPath);
    term('🦊 Deploying agent ').green(config.handle)('...\n');

    // Check that the package.json path exists in this directory.
    const packageJsonPath = path.resolve(path.join(agentPath, 'package.json'));
    if (!fs.existsSync(packageJsonPath)) {
      throw Error(`No package.json found at ${packageJsonPath}. Only JS-based agents are supported.`);
    }

    const yarnLockPath = path.resolve(path.join(agentPath, 'yarn.lock'));
    const pnpmLockPath = path.resolve(path.join(agentPath, 'pnpm-lock.yaml'));

    if (fs.existsSync(yarnLockPath)) {
      term.yellow(
        '⚠️ Detected yarn.lock file, but Fixie only supports npm. Fixie will try to install your package with npm, which may produce unexpected results.'
      );
    }
    if (fs.existsSync(pnpmLockPath)) {
      term.yellow(
        '⚠️ Detected pnpm-lock.yaml file, but Fixie only supports npm. Fixie will try to install your package with npm, which may produce unexpected results.'
      );
    }

    const agent = await this.ensureAgent({ client, config });
    const runtimeParametersSchema = this.inferRuntimeParametersSchema(agentPath);
    const tarball = FixieAgent.getCodePackage(agentPath);
    const spinner = ora(' 🚀 Deploying... (hang tight, this takes a minute or two!)').start();
    const revision = await agent.createRevision({
      tarball,
      environmentVariables,
      runtimeParametersSchema: JSON.stringify(runtimeParametersSchema),
    });
    spinner.succeed(`Agent ${config.handle} is running at: ${agent.agentUrl(client.url)}`);
    return revision;
  }

  /** Run an agent locally from the given directory. */
  public static async ServeAgent({
    client,
    agentPath,
    tunnel,
    port,
    environmentVariables,
    debug,
  }: {
    client: FixieClient;
    agentPath: string;
    tunnel?: boolean;
    port: number;
    environmentVariables: Record<string, string>;
    debug?: boolean;
  }) {
    const config = await FixieAgent.LoadConfig(agentPath);
    term('🦊 Serving agent ').green(config.handle)('...\n');

    // Check if the package.json path exists in this directory.
    const packageJsonPath = path.resolve(path.join(agentPath, 'package.json'));
    if (!fs.existsSync(packageJsonPath)) {
      throw Error(`No package.json found in ${packageJsonPath}. Only JS-based agents are supported.`);
    }

    // Infer the runtime parameters schema. We'll create a generator that yields whenever the schema changes.
    let runtimeParametersSchema = FixieAgent.inferRuntimeParametersSchema(agentPath);
    const { iterator: schemaGenerator, push: pushToSchemaGenerator } =
      this.createAsyncIterable<TJS.Definition | null>();
    pushToSchemaGenerator(runtimeParametersSchema);

    // Start the agent process locally.
    let agentProcess = FixieAgent.spawnAgentProcess(agentPath, port, environmentVariables);

    // Watch files in the agent directory for changes.
    const watchPath = path.resolve(agentPath);
    const watchExcludePaths = [
      path.resolve(path.join(agentPath, 'dist')),
      path.resolve(path.join(agentPath, 'node_modules')),
    ];
    // Return true if the path matches the prefix of any of the exclude paths.
    const ignoreFunc = (path: string): boolean => {
      if (watchExcludePaths.some((excludePath) => path.startsWith(excludePath))) {
        return true;
      }
      return false;
    };
    console.log(`🌱 Watching ${watchPath} for changes...`);

    const watcher = new Watcher(watchPath, {
      ignoreInitial: true,
      recursive: true,
      ignore: ignoreFunc,
    });
    watcher.on('all', async (event: any, targetPath: string, _targetPathNext: any) => {
      console.log(`🌱 Restarting local agent process due to ${event}: ${targetPath}`);
      agentProcess.kill();
      // Let it shut down gracefully.
      await new Promise<void>((resolve) => {
        if (agentProcess.exitCode !== null || agentProcess.signalCode !== null) {
          resolve();
        } else {
          agentProcess.on('close', () => {
            resolve();
          });
        }
      });

      try {
        const newSchema = FixieAgent.inferRuntimeParametersSchema(agentPath);
        if (JSON.stringify(runtimeParametersSchema) !== JSON.stringify(newSchema)) {
          pushToSchemaGenerator(newSchema);
          runtimeParametersSchema = newSchema;
        }

        agentProcess = FixieAgent.spawnAgentProcess(agentPath, port, environmentVariables);
      } catch (ex) {
        term(`❌ Failed to restart agent process: ${ex} \n`);
      }
    });

    // This is an iterator which yields the public URL of the tunnel where the agent
    // can be reached by the Fixie service. The tunnel address can change over time.
    let deploymentUrlsIter: AsyncIterator<string>;
    if (tunnel) {
      deploymentUrlsIter = FixieAgent.spawnTunnel(port, Boolean(debug));
    } else {
      if (!config.deploymentUrl) {
        throw Error('No deployment URL specified in agent.yaml');
      }
      deploymentUrlsIter = (async function* () {
        yield config.deploymentUrl!;

        // Never yield another value.
        await new Promise(() => {});
      })();
    }

    const agent = await this.ensureAgent({ client, config });
    const originalRevision = await agent.getCurrentRevision();
    if (originalRevision) {
      term('🥡 Replacing current agent revision ').green(originalRevision.revisionId)('\n');
    }
    let currentRevision: AgentRevision | null = null;
    const doCleanup = async () => {
      watcher.close();
      if (originalRevision) {
        try {
          await agent.setCurrentRevision(originalRevision.revisionId);
          term('🥡 Restoring original agent revision ').green(originalRevision.revisionId)('\n');
        } catch (e: any) {
          term('🥡 Failed to restore original agent revision: ').red(e.message)('\n');
        }
      }
      if (currentRevision) {
        try {
          await agent.deleteRevision(currentRevision.revisionId);
          term('🥡 Deleting temporary agent revision ').green(currentRevision.revisionId)('\n');
        } catch (e: any) {
          term('🥡 Failed to delete temporary agent revision: ').red(e.message)('\n');
        }
      }
    };
    process.on('SIGINT', async () => {
      console.log('Got Ctrl-C - cleaning up and exiting.');
      await doCleanup();
    });

    // The tunnel may yield different URLs over time. We need to create a new
    // agent revision each time.
    for await (const [currentUrl, runtimeParametersSchema] of this.zipAsyncIterables(
      deploymentUrlsIter,
      schemaGenerator
    )) {
      await FixieAgent.pollPortUntilReady(port);

      term('🚇 Current tunnel URL is: ').green(currentUrl)('\n');
      try {
        if (currentRevision) {
          term('🥡 Deleting temporary agent revision ').green(currentRevision.revisionId)('\n');
          await agent.deleteRevision(currentRevision.revisionId);
          currentRevision = null;
        }
        currentRevision = await agent.createRevision({
          externalUrl: currentUrl,
          runtimeParametersSchema: JSON.stringify(runtimeParametersSchema),
        });
        term('🥡 Created temporary agent revision ').green(currentRevision.revisionId)('\n');
        term('🥡 Agent ').green(config.handle)(' is running at: ').green(agent.agentUrl(client.url))('\n');
      } catch (e: any) {
        term('🥡 Got error trying to create agent revision: ').red(e.message)('\n');
        console.error(e);
        continue;
      }
    }
  }

  private static async pollPortUntilReady(port: number): Promise<void> {
    while (true) {
      try {
        await new Promise<void>((resolve, reject) => {
          const socket = net.connect({
            host: '127.0.0.1',
            port,
          });

          socket.on('connect', resolve);
          socket.on('error', reject);
        });
        break;
      } catch {
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
    }
  }

  private static createAsyncIterable<T>(): { iterator: AsyncIterator<T>; push: (value: T) => void } {
    let streamController: ReadableStreamDefaultController<T>;
    const stream = new ReadableStream<T>({
      start(controller) {
        streamController = controller;
      },
    });

    return {
      // @ts-expect-error https://github.com/DefinitelyTyped/DefinitelyTyped/discussions/62651
      iterator: stream[Symbol.asyncIterator](),
      push: (value: T) => {
        streamController.enqueue(value);
      },
    };
  }

  private static async *zipAsyncIterables<T, U>(
    gen1: AsyncIterator<T>,
    gen2: AsyncIterator<U>
  ): AsyncGenerator<[T, U]> {
    const generators = [gen1, gen2] as const;
    const currentValues = (await Promise.all(generators.map((g) => g.next()))).map((v) => v.value) as [T, U];
    const nextPromises = generators.map((g) => g.next());

    async function updateWithReadyValue(index: number): Promise<boolean> {
      const value = await Promise.race([nextPromises[index], null]);
      if (value === null) {
        return false;
      }

      if (value.done) {
        return true;
      }

      currentValues[index] = value.value;
      nextPromises[index] = generators[index].next();
      return false;
    }

    while (true) {
      yield currentValues;

      // Wait for one of the generators to yield a new value.
      await Promise.race(nextPromises);

      const shouldExit = await Promise.all([0, 1].map(updateWithReadyValue));
      if (shouldExit.some((v) => v)) {
        break;
      }
    }
  }

  private static spawnTunnel(port: number, debug: boolean): AsyncIterator<string> {
    const { iterator, push: pushToIterator } = this.createAsyncIterable<string>();

    term('🚇 Starting tunnel process...\n');
    // We use localhost.run as a tunneling service. This sets up an SSH tunnel
    // to the provided local port via localhost.run. The subprocess returns a
    // stream of JSON responses, one per line, with the external URL of the tunnel
    // as it changes.
    const subProcess = execa('ssh', [
      '-R',
      // N.B. 127.0.0.1 must be used on Windows (not localhost or 0.0.0.0)
      `80:127.0.0.1:${port}`,
      '-o',
      // Need to send keepalives to prevent the connection from getting chopped
      // (see https://localhost.run/docs/faq#my-connection-is-unstable-tunnels-go-down-often)
      'ServerAliveInterval=59',
      '-o',
      'StrictHostKeyChecking=accept-new',
      'nokey@localhost.run',
      '--',
      '--output=json',
    ]);
    subProcess.stdout?.setEncoding('utf8');

    // Every time the subprocess emits a new line, we parse it as JSON ans
    // extract the 'address' field.
    let currentLine = '';
    subProcess.stdout?.on('data', (chunk: string) => {
      // We need to do buffering since the data we get from stdout
      // will not necessarily be line-buffered. We can get 0, 1, or more complete
      // lines in a single chunk.
      currentLine += chunk;
      let newlineIndex;
      while ((newlineIndex = currentLine.indexOf('\n')) !== -1) {
        const line = currentLine.slice(0, newlineIndex);
        currentLine = currentLine.slice(newlineIndex + 1);
        // Parse data as JSON.
        const pdata = JSON.parse(line);
        // If pdata has the 'address' field, yield it.
        if (pdata.address) {
          pushToIterator(`https://${pdata.address}`);
        }
      }
    });

    subProcess.stderr?.on('data', (sdata: string) => {
      if (debug) {
        console.error(`🚇 Tunnel stderr: ${sdata}`);
      }
    });
    subProcess.on('close', (returnCode: number) => {
      if (debug) {
        console.log(`🚇 Tunnel child process exited with code ${returnCode}`);
      }
      iterator.return?.(null);
    });

    return iterator;
  }
}
