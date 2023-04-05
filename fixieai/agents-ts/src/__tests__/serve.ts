import fs from 'fs';
import got from 'got';
import yaml from 'js-yaml';
import nock from 'nock';
import path from 'path';
import serve, { AgentConfig } from '../serve';

const agentConfigPath = path.resolve(__dirname, '..', 'fixtures', 'agent.yaml');
const agentConfigContents = fs.readFileSync(agentConfigPath, 'utf8');
const agentConfig = yaml.load(agentConfigContents) as AgentConfig;

const refreshMetadataAPIUrl = 'http://fake:3000/refresh-metadata';

const refreshMetadataHostname = new URL(refreshMetadataAPIUrl).hostname;
nock('http://fake:3000').post('/refresh-metadata').reply(200, {});

describe('error handling', () => {
  it('throws an error if the entry point does not exist', async () => {
    await expect(async () =>{
      const close = await serve({
        agentConfigPath: 'agent.yaml',
        agentConfig: {
          ...agentConfig,
          entry_point: 'does-not-exist.ts',
        },
        port: 3000,
        silentStartup: true,
        refreshMetadataAPIUrl,
      })
      close();
    }).rejects.toThrowError(
      /The entry point \(.*\) does not exist. Did you specify the wrong path in your agent.yaml\? The entry_point is interpreted relative to the agent.yaml./,
    );
  });
});

it('Agent metadata', async () => {
  const port = 3000;
  const silentStartup = true;

  const close = await serve({
    agentConfigPath,
    agentConfig,
    port,
    silentStartup,
    refreshMetadataAPIUrl,
    silentRequestHandling: true,
  });
  try {
    const response = await got(`http://localhost:${port}`);

    expect(response.statusCode).toBe(200);
    expect(response.body).toEqual(JSON.stringify({
      base_prompt: `I'm an agent that rolls virtual dice!`,
      few_shots: [
        `
Q: Roll a d20
Ask Func[roll]: 20 1
Func[roll] says: 12
A: You rolled a 12!`,
        `Q: Roll two dice and blow on them first for good luck
Ask Func[roll]: 6 2
Func[roll] says: 4 3
A: You rolled a 4 and a 3, with a total of 7.`,
        `Q: Roll 3d8
Ask Func[roll]: 8 3
Func[roll] says: 5 3 8
A: You rolled 5, 3, and 8, for a total of 16.
`,
      ],
    }));
  } finally {
    close();
  }
});
