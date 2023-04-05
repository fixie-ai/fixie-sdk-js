import fs from 'fs';
import got from 'got';
import yaml from 'js-yaml';
import path from 'path';
import serve, { AgentConfig } from '../serve';

const agentConfigPath = path.resolve(__dirname, '..', 'fixtures', 'agent.yaml');
const agentConfigContents = fs.readFileSync(agentConfigPath, 'utf8');
const agentConfig = yaml.load(agentConfigContents) as AgentConfig;

describe('error handling', () => {
  it('throws an error if the entry point does not exist', async () => {
    await expect(() => serve('agent.yaml', { 
      ...agentConfig,
      entry_point: 'does-not-exist.ts' 
    }, 3000, true)).rejects.toThrowError(/The entry point \(.*\) does not exist. Did you specify the wrong path in your agent.yaml\? The entry_point is interpreted relative to the agent.yaml./);
  });
});

it('Agent metadata', async () => {
  const port = 3000;
  const silentStartup = true;

  const close = await serve(agentConfigPath, agentConfig, port, silentStartup, true);

  const response = await got(`http://localhost:${port}`);

  expect(response.statusCode).toBe(200);
  expect(response.body).toEqual(JSON.stringify({
    base_prompt: "General info about what this agent does and the tone it should use.",
    few_shots: [`
Q: Sample query to this agent
A: Sample response`, `Q: Another sample query
Ask Func[example]: input
Func[example] says: output
A: The other response is output
`],
  }));

  close();
});
