import fsSync from 'fs';
import fs from 'fs/promises';
import got from 'got';
import yaml from 'js-yaml';
import nock from 'nock';
import path from 'path';
import tempy from 'tempy';
import type { PromiseType } from 'utility-types';
import serve, { AgentConfig } from '../serve';

const agentConfigPath = path.resolve(__dirname, '..', 'fixtures', 'agent.yaml');
const agentConfigContents = fsSync.readFileSync(agentConfigPath, 'utf8');
const agentConfig = yaml.load(agentConfigContents) as AgentConfig;

const refreshMetadataAPIUrl = 'http://fake:3000/refresh-metadata';

nock(new URL(refreshMetadataAPIUrl).origin).post('/refresh-metadata').times(Infinity).reply(200, {});

it('throws an error if the entry point does not exist', async () => {
  await expect(async () => {
    const close = await serve({
      agentConfigPath: 'agent.yaml',
      agentConfig: {
        ...agentConfig,
        entry_point: 'does-not-exist.ts',
      },
      port: 3000,
      silentStartup: true,
      refreshMetadataAPIUrl,
    });
    close();
  }).rejects.toThrowError(
    /The entry point \(.*\) does not exist. Did you specify the wrong path in your agent.yaml\? The entry_point is interpreted relative to the agent.yaml./,
  );
});

const port = 3000;
describe('server starts', () => {
  // If `serve` throws an error, then `close` will be undefined. Jest will invoke the tests even if `beforeEach` throws.
  let close: PromiseType<ReturnType<typeof serve>> | undefined;

  beforeEach(async () => {
    close = await serve({
      agentConfigPath,
      agentConfig,
      port,
      silentStartup: true,
      silentRequestHandling: true,
      refreshMetadataAPIUrl,
    });
  });

  it('Request body is not in the expected format', async () => {
    const response = await got.post(`http://localhost:${port}/roll`, {
      json: { message: { unrecognizedKey: 'invalid' } },
      throwHttpErrors: false,
    });

    expect(response.statusCode).toBe(400);
    expect(response.body).toBe(
      'Request body must be of the shape: {"message": {"text": "your input to the function"}}. However, the body was: {"message":{"unrecognizedKey":"invalid"}}',
    );
  });

  it('Function being called does not exist', async () => {
    const response = await got.post(`http://localhost:${port}/function-does-not-exist`, {
      json: { message: { text: 'input' } },
      throwHttpErrors: false,
    });

    expect(response.statusCode).toBe(404);
    expect(response.body).toBe(
      'Function not found: function-does-not-exist. Functions available: roll, willThrowError, willThrowErrorAsync, rollAsync',
    );
  });

  describe('sync functions', () => {
    it('calls a function', async () => {
      const response = await got.post(`http://localhost:${port}/roll`, {
        responseType: 'json',
        json: { message: { text: '20 1' } },
      });
      expect(response.statusCode).toBe(200);
      const diceResult = Number((response.body as any).message.text);
      expect(diceResult).not.toBeNaN();
      expect(diceResult).toBeGreaterThanOrEqual(1);
      expect(diceResult).toBeLessThanOrEqual(20);
    });

    it('Function being called throws an error', async () => {
      const response = await got.post(`http://localhost:${port}/willThrowError`, {
        json: { message: { text: 'input' } },
        throwHttpErrors: false,
      });

      expect(response.statusCode).toBe(500);
      expect(response.body).toMatch(/Error: This is an error/);
    });
  });

  describe('async functions', () => {
    it('calls a function', async () => {
      const response = await got.post(`http://localhost:${port}/rollAsync`, {
        responseType: 'json',
        json: { message: { text: '10 1' } },
      });
      expect(response.statusCode).toBe(200);
      const diceResult = Number((response.body as any).message.text);
      expect(diceResult).not.toBeNaN();
      expect(diceResult).toBeGreaterThanOrEqual(1);
      expect(diceResult).toBeLessThanOrEqual(10);
    });

    it('Function being called throws an error', async () => {
      const response = await got.post(`http://localhost:${port}/willThrowErrorAsync`, {
        json: { message: { text: 'input' } },
        throwHttpErrors: false,
      });

      expect(response.statusCode).toBe(500);
      expect(response.body).toMatch(/Error: This is an async error/);
    });
  });

  it('Agent metadata', async () => {
    const response = await got(`http://localhost:${port}`);

    expect(response.statusCode).toBe(200);
    expect(response.body).toEqual(JSON.stringify({
      base_prompt: "I'm an agent that rolls virtual dice!",
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
  });

  afterEach(() => {
    close?.();
  });
});

it('watch mode', async () => {
  const temporaryAgentConfigPath = tempy.file({ extension: 'yaml' });
  const temporaryAgentTSPath = tempy.file({ extension: 'ts' });

  const temporaryAgentConfig = {
    ...agentConfig,
    entry_point: temporaryAgentTSPath,
  };

  await fs.writeFile(temporaryAgentConfigPath, yaml.dump(temporaryAgentConfig));

  const agentTSPath = path.resolve(path.dirname(agentConfigPath), agentConfig.entry_point);
  await fs.copyFile(agentTSPath, temporaryAgentTSPath);

  let close;
  try {
    close = await serve({
      agentConfigPath: temporaryAgentConfigPath,
      agentConfig: temporaryAgentConfig,
      port,
      silentStartup: true,
      watch: true,
      silentRequestHandling: true,
      refreshMetadataAPIUrl,
    });

    const response = await got(`http://localhost:${port}`);
    expect(JSON.parse(response.body)).toEqual(
      expect.objectContaining({ base_prompt: "I'm an agent that rolls virtual dice!" }),
    );

    /**
     * This is a little spooky, because it means we're not testing one of the core pieces of logic: that the server
     * properly clears the NodeJS require cache before reloading the file. However, without this line, Jest's own
     * require cache muckery interferes with what the server does, thereby breaking the test.
     *
     * I tested manually and the server's cache clearing behavior works. 👻🤪
     */
    jest.resetModules();

    const orginalTSContents = await fs.readFile(temporaryAgentTSPath, 'utf8');
    const modifiedTSContents = orginalTSContents.replace(
      "I'm an agent that rolls virtual dice!",
      "I'm a modified agent!",
    );
    await fs.writeFile(temporaryAgentTSPath, modifiedTSContents);
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const responseAfterWatch = await got(`http://localhost:${port}`);
    expect(JSON.parse(responseAfterWatch.body)).toEqual(
      expect.objectContaining({ base_prompt: "I'm a modified agent!" }),
    );
  } finally {
    await close?.();
  }
});
