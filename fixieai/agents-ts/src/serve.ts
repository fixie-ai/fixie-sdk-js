import path from 'path';

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

function validate(agentConfigPath: string, agentConfig: AgentConfig) {
  const entryPointPath = path.relative(agentConfigPath, agentConfig.entry_point)
  let agent;
  try {
    agent = require(entryPointPath);
  } catch (e: any) {
    if (e.code === 'MODULE_NOT_FOUND') {
      const absolutePath = path.resolve(entryPointPath);
      throw new Error(`The entry point (${absolutePath}) does not exist. Did you specify the wrong path in your agent.yaml? The entry_point is interpreted relative to the agent.yaml.`);
    }
  }
}

export default function serve(agentConfigPath: string, agentConfig: AgentConfig, port: number) {
  validate(agentConfigPath, agentConfig);
}
