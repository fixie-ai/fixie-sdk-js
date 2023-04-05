#! /usr/bin/env node

import fs from 'fs';
import yaml from 'js-yaml';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';
import serve, { AgentConfig } from './serve';

const { argv } = yargs(hideBin(process.argv))
  .scriptName('cli-tool')
  .options({
    port: {
      describe: 'Port to listen on',
      type: 'number',
      required: true,
    },
    agent: {
      describe: 'Path to the agent.yaml',
      type: 'string',
      required: true,
      default: 'config.yaml',
      coerce: (path: string): { parsed: AgentConfig; path: string; } => {
        let fileContents;
        try {
          fileContents = fs.readFileSync(path, 'utf8');
        } catch (e) {
          if ((e as any).code === 'ENOENT') {
            throw new Error(`The provided path (${path}) does not exist.`);
          }
          throw e;
        }
        try {
          const parsed = yaml.load(fileContents) as AgentConfig;
          return { parsed, path };
        } catch (e: any) {
          throw new Error(`The provided path (${path}) is not a valid YAML file. The error was:\n${e.toString()}`);
        }
      },
    },
  })
  .strict()
  .help();

/**
 * This is a little dance to make TS happy. We know that argv is not a Promise, based on how we wrote the yargs code,
 * based but TS doesn't.
 */
type ExcludePromiseType<T> = Exclude<T, Promise<any>>;
const staticArgv = argv as ExcludePromiseType<typeof argv>;

serve(staticArgv.agent.path, staticArgv.agent.parsed, staticArgv.port);
