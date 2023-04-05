import fs from 'fs';
import path from 'path';
import express from 'express';
import bodyParser from 'body-parser';
import _ from 'lodash';

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
  basePrompt: string;
  fewShots: string[];
}

interface AgentResponse {
  message: Message;
}
interface Message {
  text: string;
}

type AgentFunc = (args: string) => string;

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
      throw new Error(`Agent must have a string export named BASE_PROMPT. The agent exported the following: ${allExports}.`);
    }
    if (typeof requiredAgent.FEW_SHOTS !== 'string') {
      throw new Error(`Agent must have a string export named FEW_SHOTS. The agent exported the following: ${allExports}`);
    }
    const funcs = _.omit(requiredAgent, 'basePrompt', 'fewShots');

    this.agent = {
      basePrompt: requiredAgent.BASE_PROMPT,
      fewShots: requiredAgent.FEW_SHOTS,
      funcs
    }
  }

  runFunction(funcName: string, args: Parameters<AgentFunc>[0]): ReturnType<AgentFunc> {
    const func = this.agent.funcs[funcName];
    if (!func) {
      throw new FunctionNotFoundError(`Function not found: ${funcName}. Functions available: ${Object.keys(this.agent.funcs).join(', ')}`);
    }
    return func(args);
  }

  getAgentMetadata(): AgentMetadata {
    return {
      basePrompt: this.agent.basePrompt,
      fewShots: this.agent.fewShots,
    };
  }
}

export default async function serve(agentConfigPath: string, agentConfig: AgentConfig, port: number) {
  const entryPointPath = path.resolve(path.dirname(agentConfigPath), agentConfig.entry_point);
  if (!fs.existsSync(entryPointPath)) {
    const absolutePath = path.resolve(entryPointPath);
    throw new Error(
      `The entry point (${absolutePath}) does not exist. Did you specify the wrong path in your agent.yaml? The entry_point is interpreted relative to the agent.yaml.`,
    );
  }

  const agentRunner = new AgentRunner(entryPointPath);

  const app = express();
  app.use(bodyParser.json());
  app.get('/', (_req, res) => res.send(agentRunner.getAgentMetadata()));
  app.post('/:funcName', (req, res) => {
    const funcName = req.params.funcName;
    const body = req.body;
    try {
      const result = agentRunner.runFunction(funcName, body.message.text);
      const response: AgentResponse = { message: { text: result } };
      res.send(response);
    } catch (e: any) {
      if (e.name === 'FunctionNotFoundError') {
        res.status(404).send(e.message);
      } else {
        res.status(500).send(e.toString());
      }
    }
  });
  await new Promise<void>((resolve) => app.listen(port, () => resolve()));
  console.log(`Codeshot agent listening on port ${port}.`);
}
