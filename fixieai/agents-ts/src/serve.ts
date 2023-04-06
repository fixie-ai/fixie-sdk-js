import bodyParser from 'body-parser';
import bunyan from 'bunyan';
import bunyanFormat from 'bunyan-format';
import bunyanMiddleware from 'bunyan-middleware';
import clearModule from 'clear-module';
import express from 'express';
import asyncHandler from 'express-async-handler';
import fs from 'fs';
import got from 'got';
import _ from 'lodash';
import path from 'path';
import * as tsNode from 'ts-node';
import nodemon from 'nodemon';
import { Promisable } from 'type-fest';

/**
 * This file can be called in two environmentS:
 *
 *    1. From Python: calling the compiled JS. (This is the normal case.)
 *    2. From ts-node (This is for local dev.)
 *
 * In both cases, we want to be able to `require` an Agent written in TS.
 * In case (1), we need to call tsNode.register() to enable that.
 * In case (2), we don't need to call tsNode.register(), because we're already in ts-node. And if we do call it, it
 * actually creates problems.
 */
// @ts-expect-error
// eslint-disable-next-line @typescript-eslint/strict-boolean-expressions
if (!process[Symbol.for('ts-node.register.instance')]) {
  tsNode.register();
}

/**
 * This should be kept in sync with the `AgentConfig` dataclass.
 */
export interface AgentConfig {
  handle: string;
  name?: string;
  description: string;
  more_info_url: string;
  language: string;
  entry_point: string;
  deployment_url?: string;
  public?: boolean;
}

interface AgentMetadata {
  base_prompt: string;
  few_shots: string[];
}
interface Message {
  text: string;
}
interface AgentResponse {
  message: Message;
}

type AgentFunc = (args: string) => Promisable<string>;

interface Agent {
  basePrompt: string;
  fewShots: string[];
  funcs: Record<string, AgentFunc>;
}

class FunctionNotFoundError extends Error {
  name = 'FunctionNotFoundError';
}

class AgentRunner {
  private readonly agent: Agent;

  constructor(agentPath: string) {
    const requiredAgent = require(agentPath);
    const allExports = Object.keys(requiredAgent).join(', ');

    if (typeof requiredAgent.BASE_PROMPT !== 'string') {
      throw new Error(
        `Agent must have a string export named BASE_PROMPT. The agent exported the following: ${allExports}.`,
      );
    }
    if (typeof requiredAgent.FEW_SHOTS !== 'string') {
      throw new Error(
        `Agent must have a string export named FEW_SHOTS. The agent exported the following: ${allExports}.`,
      );
    }
    const funcs = _.omit(requiredAgent, 'BASE_PROMPT', 'FEW_SHOTS');

    this.agent = {
      basePrompt: requiredAgent.BASE_PROMPT,
      fewShots: requiredAgent.FEW_SHOTS.split('\n\n'),
      funcs,
    };
  }

  runFunction(funcName: string, args: Parameters<AgentFunc>[0]): ReturnType<AgentFunc> {
    if (!(funcName in this.agent.funcs)) {
      throw new FunctionNotFoundError(
        `Function not found: ${funcName}. Functions available: ${Object.keys(this.agent.funcs).join(', ')}`,
      );
    }
    return this.agent.funcs[funcName](args);
  }

  getAgentMetadata(): AgentMetadata {
    return {
      base_prompt: this.agent.basePrompt,
      few_shots: this.agent.fewShots,
    };
  }
}

/**
 * TODO:
 *  - watch mode
 *  - logger formatting for local dev
 */

export default async function serve({
  agentConfigPath,
  agentConfig,
  port,
  silentStartup,
  refreshMetadataAPIUrl,
  watch = false,
  silentRequestHandling = false,
  humanReadableLogs = false,
}: {
  agentConfigPath: string;
  agentConfig: AgentConfig;
  port: number;
  silentStartup: boolean;
  refreshMetadataAPIUrl?: string;
  watch?: boolean;
  silentRequestHandling?: boolean;
  humanReadableLogs?: boolean;
}) {
  const entryPointPath = path.resolve(
    path.dirname(agentConfigPath),
    agentConfig.entry_point,
  );
  if (!fs.existsSync(entryPointPath)) {
    const absolutePath = path.resolve(entryPointPath);
    throw new Error(
      `The entry point (${absolutePath}) does not exist. Did you specify the wrong path in your agent.yaml? The entry_point is interpreted relative to the agent.yaml.`,
    );
  }

  let agentRunner = new AgentRunner(entryPointPath);
  if (watch) {
    const entryPointDir = path.dirname(entryPointPath);
    nodemon({
      script: `${require.resolve('../empty-bin')} --help`,
      watch: [entryPointDir],
    })
      .on('start', () => console.log(`Watching ${entryPointDir} for changes...`))
      .on('restart', () => {
        clearModule(entryPointPath);
        agentRunner = new AgentRunner(entryPointPath);
        console.log('Server reloaded for agent change');
      })
  }

  const app = express();

  function getLogStream() {
    if (silentRequestHandling) {
      return [];
    }
    if (humanReadableLogs) {
      // This looks pretty bad but we can iterate on it later.
      return [{ stream: bunyanFormat({ outputMode: 'short' }) }];
    }
    return [{ stream: process.stdout }];
  }

  const logger = bunyan.createLogger({
    name: 'fixie-serve',
    streams: getLogStream(),
  });
  app.use(bunyanMiddleware(logger));

  app.use(bodyParser.json());

  app.get('/', (_req, res) => res.send(agentRunner.getAgentMetadata()));
  app.post(
    '/:funcName',
    asyncHandler(async (req, res) => {
      const funcName = req.params.funcName;
      const body = req.body;

      if (typeof req.body.message?.text !== 'string') {
        res
          .status(400)
          // Is it a security problem to stringify untrusted input?
          .send(
            `Request body must be of the shape: {"message": {"text": "your input to the function"}}. However, the body was: ${
              JSON.stringify(
                req.body,
              )
            }`,
          );
        return;
      }

      try {
        const result = await agentRunner.runFunction(funcName, body.message);
        const response: AgentResponse = { message: { text: result } };
        res.send(response);
      } catch (e: any) {
        if (e.name === 'FunctionNotFoundError') {
          res.status(404).send(e.message);
          return;
        }
        const errorForLogging = _.pick(e, 'message', 'stack');
        logger.error(
          { error: errorForLogging, functionName: funcName },
          'Error running agent function',
        );
        res.status(500).send(errorForLogging);
      }
    }),
  );
  const server = await new Promise<ReturnType<typeof app.listen>>((resolve) => {
    const server = app.listen(port, () => resolve(server));
  });
  if (refreshMetadataAPIUrl !== undefined) {
    await got.post(refreshMetadataAPIUrl);
  }
  if (!silentStartup) {
    console.log(`Agent listening on port ${port}.`);
  }

  return server.close.bind(server);
}
