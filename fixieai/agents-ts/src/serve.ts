import bodyParser from 'body-parser';
import bunyan from 'bunyan';
import bunyanFormat from 'bunyan-format';
import bunyanMiddleware from 'bunyan-middleware';
import express from 'express';
import got from 'got';
import _ from 'lodash';
import path from 'path';
import * as tsNode from 'ts-node';

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
  /**
   * We may need to explicitly pass the tsconfig.json here. Let's try omitting it and see if that works.
   */
  tsNode.register();
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
export interface FuncParam {
  text: string;
}
export type AgentFunc = (funcParam: FuncParam) => string;

interface Agent {
  basePrompt: string;
  fewShots: string[];
  funcs: Record<string, AgentFunc>;
}

class FunctionNotFoundError extends Error {
  name = 'FunctionNotFoundError';
}

class ErrorWrapper extends Error {
  constructor(readonly message: string, readonly innerError: Error) {
    super(message);
  }
}

class FuncHost {
  private readonly agent: Agent;

  constructor(packagePath: string) {
    const absolutePath = path.resolve(packagePath);
    try {
      const requiredAgent = require(absolutePath);
      const allExports = Object.keys(requiredAgent).join(', ');

      if (typeof requiredAgent.BASE_PROMPT !== 'string') {
        throw new Error(
          `Agent must have a string export named BASE_PROMPT. The agent at ${absolutePath} exported the following: "${allExports}".`,
        );
      }
      if (typeof requiredAgent.FEW_SHOTS !== 'string') {
        throw new Error(
          `Agent must have a string export named FEW_SHOTS. The agent at ${absolutePath} exported the following: "${allExports}".`,
        );
      }
      const funcs = _.omit(requiredAgent, 'BASE_PROMPT', 'FEW_SHOTS');

      this.agent = {
        basePrompt: requiredAgent.BASE_PROMPT,
        fewShots: requiredAgent.FEW_SHOTS.split('\n\n'),
        funcs,
      };
    } catch (e: any) {
      if (e.code === 'MODULE_NOT_FOUND') {
        throw new ErrorWrapper(
          `Could not find package at path: ${absolutePath}. Does this path exist? If it does, did you specify a "main" field in your package.json?`,
          e,
        );
      }
      throw e;
    }
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
 *  - async agent functions
 */

export default async function serve({
  packagePath,
  port,
  silentStartup,
  refreshMetadataAPIUrl,
  silentRequestHandling = false,
  humanReadableLogs = false,
}: {
  packagePath: string;
  port: number;
  silentStartup: boolean;
  refreshMetadataAPIUrl?: string;
  silentRequestHandling?: boolean;
  humanReadableLogs?: boolean;
}) {
  const agentRunner = new FuncHost(packagePath);

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
  app.post('/:funcName', (req, res) => {
    const funcName = req.params.funcName;

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

    const body = req.body as AgentResponse;

    try {
      const result = agentRunner.runFunction(funcName, body.message);
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
  });
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
