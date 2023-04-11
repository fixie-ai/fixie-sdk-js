import fs from 'fs/promises';
import got from 'got';
import nock from 'nock';
import path from 'path';
import tempy from 'tempy';
import { Jsonifiable } from 'type-fest';
import type { PromiseType } from 'utility-types';
import serve from '../serve';

/* eslint-disable id-blacklist */

const agentId = 'my-agent';
const agentPackagePath = path.resolve(__dirname, '..', 'fixtures', 'normal');
let refreshMetadataAPIUrlCallCount = 0;
const refreshMetadataAPIUrl = 'http://fake:3000/refresh-metadata';
const userStorageApiUrl = 'http://fake:3000/user-storage';

// TODO: make a `got` client to reduce duplication.

const gotClient = got.extend({
  hooks: {
    beforeError: [
      (error) => {
        console.log(error);
        console.log(error.response?.body);
        return error;
      },
    ],
  },
});

const mockDataStore: Record<string, Jsonifiable> = {};
nock(new URL(userStorageApiUrl).origin, {
  reqheaders: {
    authorization: 'Bearer auth-token',
  },
}).persist()
  .get(new RegExp(`/user-storage/${agentId}/`)).reply(200, (uri) => {
    const key = uri.split('/').pop();
    return { data: mockDataStore[key!] };
  })
  .get(new RegExp(`/user-storage/${agentId}`)).reply(200, () => Object.keys(mockDataStore).map((key) => ({ key })))
  .post(new RegExp(`/user-storage/${agentId}/`)).reply(200, (uri, requestBody) => {
    const key = uri.split('/').pop();
    mockDataStore[key!] = (requestBody as Record<string, any>).data;
  })
  .head(new RegExp(`/user-storage/${agentId}/`)).reply((uri) => {
    const key = uri.split('/').pop();
    return [key !== undefined && key in mockDataStore ? 200 : 404];
  })
  .delete(new RegExp(`/user-storage/${agentId}/`)).reply(200, (uri) => {
    const key = uri.split('/').pop();
    // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
    delete mockDataStore[key!];
  });

nock(new URL(refreshMetadataAPIUrl).origin).persist().post('/refresh-metadata').reply(
  200,
  () => {
    refreshMetadataAPIUrlCallCount++;
  },
);

test('throws an error if the entry point does not exist', async () => {
  await expect(async () => {
    const close = await serve({
      agentId,
      packagePath: 'does-not-exist',
      port: 3000,
      silentStartup: true,
      refreshMetadataAPIUrl,
      userStorageApiUrl,
    });
    close();
  }).rejects.toThrow(
    /Could not find package at path: .*does-not-exist. Does this path exist\? If it does, did you specify a "main" field in your package.json\?/,
  );
});

test('relative path to agent', async () => {
  const close = await serve({
    agentId,
    packagePath: path.relative(process.cwd(), agentPackagePath),
    port: 3000,
    silentStartup: true,
    refreshMetadataAPIUrl,
    userStorageApiUrl,
  });
  await close();
});

const port = 3000;
describe('server starts', () => {
  // If `serve` throws an error, then `close` will be undefined. Jest will invoke the tests even if `beforeEach` throws.
  let close: PromiseType<ReturnType<typeof serve>> | undefined;

  beforeEach(async () => {
    close = await serve({
      agentId,
      packagePath: agentPackagePath,
      port,
      silentStartup: true,
      silentRequestHandling: true,
      refreshMetadataAPIUrl,
      userStorageApiUrl,
    });
  });

  afterEach(() => {
    close?.();
  });

  it('request body is not in the expected format', async () => {
    const response = await got.post(`http://localhost:${port}/roll`, {
      json: { message: { unrecognizedKey: 'invalid' } },
      throwHttpErrors: false,
    });

    expect(response.statusCode).toBe(400);
    expect(response.body).toBe(
      'Request body must be of the shape: {"message": {"text": "your input to the function"}}. However, the body was: {"message":{"unrecognizedKey":"invalid"}}',
    );
  });

  it('function being called does not exist', async () => {
    const response = await got.post(`http://localhost:${port}/function-does-not-exist`, {
      json: { message: { text: 'input' } },
      throwHttpErrors: false,
    });

    expect(response.statusCode).toBe(404);
    expect(response.body).toBe(
      'Function not found: function-does-not-exist. Functions available: chartFromBinary, chartFromText, chartFromUri, deleteItem, getItem, getItems, getTextOfEmbed, hasItem, roll, rollAsync, saveItem, willThrowError, willThrowErrorAsync',
    );
  });

  describe('user storage', () => {
    const gotClientForUserStorageTests = gotClient.extend({
      headers: {
        authorization: 'Bearer auth-token',
      },
    });

    it('has no keys when there are no items', async () => {
      const response = await gotClientForUserStorageTests.post(`http://localhost:${port}/getItems`, {
        responseType: 'json',
        json: { message: { text: '' } },
      });
      expect(response.body).toStrictEqual({ message: expect.objectContaining({ text: '[]' }) });

      const hasItemResponse = await gotClientForUserStorageTests.post(`http://localhost:${port}/hasItem`, {
        responseType: 'json',
        json: { message: { text: 'key' } },
      });
      expect(hasItemResponse.body).toStrictEqual({ message: expect.objectContaining({ text: 'false' }) });
    });

    it('all key operations', async () => {
      const response = await gotClientForUserStorageTests.post(`http://localhost:${port}/saveItem`, {
        responseType: 'json',
        json: { message: { text: 'key:value' } },
      });
      expect(response.body).toStrictEqual({ message: expect.objectContaining({ text: 'Set value' }) });

      const getResponse = await gotClientForUserStorageTests.post(`http://localhost:${port}/getItem`, {
        responseType: 'json',
        json: { message: { text: 'key' } },
      });
      expect(getResponse.body).toStrictEqual({ message: expect.objectContaining({ text: 'value' }) });

      const getKeysResponse = await gotClientForUserStorageTests.post(`http://localhost:${port}/getItems`, {
        responseType: 'json',
        json: { message: { text: '' } },
      });
      expect(getKeysResponse.body).toStrictEqual({ message: expect.objectContaining({ text: '["key"]' }) });

      const hasItemResponse = await gotClientForUserStorageTests.post(`http://localhost:${port}/hasItem`, {
        responseType: 'json',
        json: { message: { text: 'key' } },
      });
      expect(hasItemResponse.body).toStrictEqual({ message: expect.objectContaining({ text: 'true' }) });

      const deleteItemResponse = await gotClientForUserStorageTests.post(`http://localhost:${port}/deleteItem`, {
        responseType: 'json',
        json: { message: { text: 'key' } },
      });
      expect(deleteItemResponse.body).toStrictEqual({ message: expect.objectContaining({ text: 'Deleted value' }) });

      const finalGetItemsResponse = await gotClientForUserStorageTests.post(`http://localhost:${port}/getItems`, {
        responseType: 'json',
        json: { message: { text: '' } },
      });
      expect(finalGetItemsResponse.body).toStrictEqual({ message: expect.objectContaining({ text: '[]' }) });
    });
  });

  describe('embeds', () => {
    it('fromBinary', async () => {
      const response = await got.post(`http://localhost:${port}/chartFromBinary`, {
        responseType: 'json',
        json: { message: { text: '' } },
      });
      expect(response.statusCode).toBe(200);
      expect(response.body).toStrictEqual(expect.objectContaining(
        {
          message: {
            text: 'here is your chart #chart',
            embeds: {
              chart: {
                content_type: 'image/webp',
                uri: expect.stringMatching(/^data:base64,/),
              },
            },
          },
        },
      ));
    });

    it('fromText', async () => {
      const response = await got.post(`http://localhost:${port}/chartFromText`, {
        responseType: 'json',
        json: { message: { text: '' } },
      });
      expect(response.statusCode).toBe(200);
      expect(response.body).toStrictEqual(expect.objectContaining(
        {
          message: {
            text: 'here is your chart #chart',
            embeds: {
              chart: {
                content_type: 'text/plain',
                uri: 'data:base64,bXkgdGV4dCBkYXRh',
              },
            },
          },
        },
      ));
    });

    it('fromUri', async () => {
      const embedUrl = new URL('https://sample-url-to-embed.com/image.webp');
      nock(embedUrl.origin).get(embedUrl.pathname).reply(200, 'image-data');

      const response = await got.post(`http://localhost:${port}/chartFromUri`, {
        responseType: 'json',
        json: { message: { text: '' } },
      });
      expect(response.statusCode).toBe(200);
      expect(response.body).toStrictEqual(expect.objectContaining({
        message: {
          text: 'here is your chart #chart',
          embeds: {
            chart: {
              content_type: 'image/webp',
              uri: 'https://sample-url-to-embed.com/image.webp',
            },
          },
        },
      }));
    });

    it('func is able to access an inbound embed', async () => {
      const response = await got.post(`http://localhost:${port}/getTextOfEmbed`, {
        responseType: 'json',
        json: {
          message: {
            text: 'chart',
            embeds: {
              chart: {
                content_type: 'image/webp',
                uri: 'data:base64,aW1hZ2UtZGF0YQ==',
              },
            },
          },
        },
      });
      expect(response.statusCode).toBe(200);
      expect(response.body).toStrictEqual(expect.objectContaining({
        message: {
          text: 'image-data',
          embeds: {},
        },
      }));
    });
  });

  describe('sync functions', () => {
    it('calls a function', async () => {
      const response = await gotClient.post(`http://localhost:${port}/roll`, {
        responseType: 'json',
        json: { message: { text: '20 1' } },
      });
      expect(response.statusCode).toBe(200);
      const diceResult = Number((response.body as any).message.text);
      expect(diceResult).not.toBeNaN();
      expect(diceResult).toBeGreaterThanOrEqual(1);
      expect(diceResult).toBeLessThanOrEqual(20);
    });

    it('function being called throws an error', async () => {
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
      const response = await gotClient.post(`http://localhost:${port}/rollAsync`, {
        responseType: 'json',
        json: { message: { text: '10 1' } },
      });
      expect(response.statusCode).toBe(200);
      const diceResult = Number((response.body as any).message.text);
      expect(diceResult).not.toBeNaN();
      expect(diceResult).toBeGreaterThanOrEqual(1);
      expect(diceResult).toBeLessThanOrEqual(10);
    });

    it('function being called throws an error', async () => {
      const response = await got.post(`http://localhost:${port}/willThrowErrorAsync`, {
        json: { message: { text: 'input' } },
        throwHttpErrors: false,
      });

      expect(response.statusCode).toBe(500);
      expect(response.body).toMatch(/Error: This is an async error/);
    });
  });

  it('agent metadata', async () => {
    const response = await got(`http://localhost:${port}`);

    expect(response.statusCode).toBe(200);
    expect(response.body).toBe(JSON.stringify({
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
});

test('watch mode', async () => {
  const tempDir = tempy.directory({ prefix: 'fixie-sdk-serve-bin-tests' });
  const temporaryAgentTSPath = path.join(tempDir, 'index.ts');
  const originalAgentPackagePath = path.resolve(__dirname, '..', 'fixtures', 'watch');

  const originalfixtureAgentTSPath = path.resolve(originalAgentPackagePath, 'index.ts');
  await fs.copyFile(originalfixtureAgentTSPath, temporaryAgentTSPath);

  let close;
  try {
    close = await serve({
      agentId,
      packagePath: tempDir,
      port,
      silentStartup: true,
      watch: true,
      silentRequestHandling: true,
      refreshMetadataAPIUrl,
      userStorageApiUrl,
    });

    const response = await got(`http://localhost:${port}`);
    expect(JSON.parse(response.body)).toStrictEqual(
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
    const originalRefreshMetadataCallCount = refreshMetadataAPIUrlCallCount;

    const orginalTSContents = await fs.readFile(temporaryAgentTSPath, 'utf8');
    const modifiedTSContents = orginalTSContents.replace(
      "I'm an agent that rolls virtual dice!",
      "I'm a modified agent!",
    );
    await fs.writeFile(temporaryAgentTSPath, modifiedTSContents);

    // This also kinda sucks but I think it'll be fine for now.
    await new Promise((resolve) => setTimeout(resolve, 2000));

    expect(refreshMetadataAPIUrlCallCount).toBe(originalRefreshMetadataCallCount + 1);

    const responseAfterWatch = await got(`http://localhost:${port}`);
    expect(JSON.parse(responseAfterWatch.body)).toStrictEqual(
      expect.objectContaining({ base_prompt: "I'm a modified agent!" }),
    );

    const tsContentsWithNewFunc = `
      ${modifiedTSContents}
      export function newFunc() { return 'newFuncResponse'; }
    `;

    jest.resetModules();
    await fs.writeFile(temporaryAgentTSPath, tsContentsWithNewFunc);
    await new Promise((resolve) => setTimeout(resolve, 2000));

    expect(refreshMetadataAPIUrlCallCount).toBe(originalRefreshMetadataCallCount + 1);

    const newFuncResponse = await gotClient.post(`http://localhost:${port}/newFunc`, {
      json: { message: { text: 'input' } },
      responseType: 'json',
    });

    expect(newFuncResponse.statusCode).toBe(200);
    expect(newFuncResponse.body).toStrictEqual({ message: expect.objectContaining({ text: 'newFuncResponse' }) });
  } finally {
    await close?.();
  }
});
