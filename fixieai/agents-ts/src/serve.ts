import bodyParser from 'body-parser';
import bunyan from 'bunyan';
import bunyanFormat from 'bunyan-format';
import bunyanMiddleware from 'bunyan-middleware';
import chokidar from 'chokidar';
import clearModule from 'clear-module';
import express from 'express';
import asyncHandler from 'express-async-handler';
import got from 'got';
import _ from 'lodash';
import path from 'path';
import * as tsNode from 'ts-node';
import { Promisable } from 'type-fest';
import { Embed, SerializedEmbed } from './embed';
import { UserStorage } from './user-storage';

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

export interface Message {
  text: string;
  embeds: Record<string, Embed>;
}
interface SerializedMessage extends Pick<Message, 'text'> {
  embeds?: Record<string, SerializedEmbed>;
}
interface SerializedMessageEnvelope {
  message: SerializedMessage;
}
export type AgentFunc = (message: Message, userStorage: UserStorage) => Promisable<string | Message>;

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

  constructor(
    absolutePackagePath: string,
  ) {
    try {
      const requiredAgent = require(absolutePackagePath);
      const allExports = Object.keys(requiredAgent).join(', ');

      if (typeof requiredAgent.BASE_PROMPT !== 'string') {
        throw new Error(
          `Agent must have a string export named BASE_PROMPT. The agent at ${absolutePackagePath} exported the following: "${allExports}".`,
        );
      }
      if (typeof requiredAgent.FEW_SHOTS !== 'string') {
        throw new Error(
          `Agent must have a string export named FEW_SHOTS. The agent at ${absolutePackagePath} exported the following: "${allExports}".`,
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
          `Could not find package at path: ${absolutePackagePath}. Does this path exist? If it does, did you specify a "main" field in your package.json?`,
          e,
        );
      }
      throw e;
    }
  }

  runFunction(
    funcName: string,
    message: Parameters<AgentFunc>[0],
    userStorage: UserStorage,
  ): ReturnType<AgentFunc> {
    if (!(funcName in this.agent.funcs)) {
      throw new FunctionNotFoundError(
        `Function not found: ${funcName}. Functions available: ${
          Object.keys(
            this.agent.funcs,
          )
            .sort()
            .join(', ')
        }`,
      );
    }
    return this.agent.funcs[funcName](message, userStorage);
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
 *  - logger formatting for local dev
 */

export default async function serve({
  packagePath,
  port,
  silentStartup,
  refreshMetadataAPIUrl,
  userStorageApiUrl,
  agentId,
  watch = false,
  silentRequestHandling = false,
  humanReadableLogs = false,
}: {
  packagePath: string;
  agentId: string;
  port: number;
  silentStartup: boolean;
  userStorageApiUrl: string;
  refreshMetadataAPIUrl?: string;
  watch?: boolean;
  silentRequestHandling?: boolean;
  humanReadableLogs?: boolean;
}) {
  const absolutePackagePath = path.resolve(packagePath);
  let funcHost = new FuncHost(absolutePackagePath);

  async function postToRefreshMetadataUrl() {
    if (refreshMetadataAPIUrl !== undefined) {
      await got.post(refreshMetadataAPIUrl);
    }
  }

  const app = express();

  let watcher: ReturnType<typeof chokidar.watch> | undefined;
  if (watch) {
    /**
     * This will only watch the dir (and subdirs) that contain the entry point. If the entry point depends on files
     * outside its directory, the watcher won't watch them. This is a potential rough edge but it's also the way
     * Nodemon works, and I think it's unlikely to be a problem in practice.
     */
    watcher = chokidar
      .watch(absolutePackagePath, {
        /**
         * We may eventually want to change this to ignore all gitignores.
         */
        ignored: /node_modules/,
        ignoreInitial: true,
      })
      .on('all', async (_ev, filePath) => {
        const previousAgent = funcHost.getAgentMetadata();

        clearModule(absolutePackagePath);
        funcHost = new FuncHost(absolutePackagePath);

        if (!_.isEqual(previousAgent, funcHost.getAgentMetadata())) {
          await postToRefreshMetadataUrl();
        }
        console.log(`Reloading agent because "${filePath}" changed`);
      });
    console.log(`Watching ${absolutePackagePath} for changes...`);
  }

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

  app.get('/', (_req, res) => res.send(funcHost.getAgentMetadata()));
  app.post(
    '/:funcName',
    asyncHandler(async (req, res) => {
      const funcName = req.params.funcName;

      logger.debug(_.pick(req, 'body', 'params'), 'Handling request');

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

      function getAuthToken(headers: typeof req.headers): string | undefined {
        const authorizationHeader = headers.authorization;
        if (authorizationHeader === undefined) {
          return undefined;
        }
        const match = authorizationHeader.match(/^Bearer (.*)$/);
        if (match === null) {
          logger.debug(
            { authHeader: authorizationHeader },
            'Authorization header did not match expected format, so no auth header will be passed to the UserStorage client.',
          );
          return undefined;
        }
        return match[1];
      }

      const body = req.body as SerializedMessageEnvelope;
      const reqMessage = messageOfSerializedMessage(body.message);

      function serializedMessageOfMessage(message: Message): SerializedMessage {
        const result: Partial<SerializedMessage> = _.pick(message, 'text');
        result.embeds = _.mapValues(message.embeds, (e) => e.serialize());
        return result as SerializedMessage;
      }

      function messageOfSerializedMessage(serializedMessage: SerializedMessage): Message {
        return {
          ..._.pick(serializedMessage, 'text'),
          embeds: _.mapValues(serializedMessage.embeds, (e) => new Embed(e.content_type, e.uri)),
        };
      }

      try {
        const userStorage = new UserStorage(
          userStorageApiUrl,
          agentId,
          /**
           * We'll assert that auth token is defined. If it isn't, the client will throw errors, but that's fine for
           * now. We don't have any sort of better fallback.
           */
          getAuthToken(req.headers)!,
          logger,
        );
        const result = await funcHost.runFunction(
          funcName,
          reqMessage,
          userStorage,
        );
        const resMessage = typeof result === 'string' ? { text: result, embeds: {} } : result;
        const agentResponse: SerializedMessageEnvelope = { message: serializedMessageOfMessage(resMessage) };
        res.send(agentResponse);
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

  await postToRefreshMetadataUrl();

  if (!silentStartup) {
    console.log(`Agent listening on port ${port}.`);
  }

  return async () => {
    server.close();
    await watcher?.close();
  };
}
