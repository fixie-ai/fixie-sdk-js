import fs from 'fs';
import got from 'got';
import yaml from 'js-yaml';
import path from 'path';
import serve, { AgentConfig } from '../serve';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const agentConfigPath = path.join(__dirname, 'test_agent.yaml');
const agentConfigContents = fs.readFileSync(agentConfigPath, 'utf8');
const agentConfig = yaml.load(agentConfigContents) as AgentConfig;

describe('error handling', () => {
  it('throws an error if the entry point does not exist', () => {
    expect(() => serve('agent.yaml', { 
      ...agentConfig,
      entry_point: 'does-not-exist.ts' 
    }, 3000, true)).toThrow();
  });
});

it('Agent metadata', async () => {
  const port = 3000;
  const silentStartup = true;

  await serve(agentConfigPath, agentConfig, port, silentStartup);

  const response = await got(`http://localhost:${port}`);

  expect(response.statusCode).toBe(200);
  expect(response.body).toEqual(JSON.stringify({
    base_prompt: "Hello! I'm a test agent. How can I help you today?",
    few_shots: ['What can you do?', 'How do I get started?'],
  }));
});
