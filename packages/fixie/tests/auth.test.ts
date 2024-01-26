/** Unit tests for auth.ts. */

import { jest, beforeEach, afterEach, describe, expect, it } from '@jest/globals';
import { loadConfig, Authenticate } from '../src/auth';

/** This function mocks out 'fetch' to return the given response. */
const mockFetch = (response: any) => {
  const mock = jest
    .fn<typeof global.fetch>()
    .mockImplementation((_input: RequestInfo | URL, _init?: RequestInit | undefined) => {
      return Promise.resolve({
        ok: true,
        json: () => response,
      } as Response);
    });
  global.fetch = mock;
  return mock;
};

describe('FixieConfig tests', () => {
  beforeEach(() => {
    process.env = {};
  });
  it('loadConfig reads fixie CLI config', async () => {
    const config = loadConfig('tests/fixtures/test-fixie-config.yaml');
    expect(config.apiUrl).toBe('https://fake.api.domain');
    expect(config.apiKey).toBe('test-api-key');
  });
  it('loadConfig ignores unknown fields', async () => {
    const config = loadConfig('tests/fixtures/test-fixie-config-ignore-fields.yaml');
    expect(config.apiUrl).toBe('https://fake.api.domain');
    expect(config.apiKey).toBe('test-api-key');
  });
});

describe('Authenticate tests', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });
  it('Authenticate returns authenticated client', async () => {
    mockFetch({
      user: {
        userId: 'fake-user-id',
        email: 'bob@bob.com',
        fullName: 'Bob McBeef',
      },
    });
    const client = await Authenticate({ configFile: 'tests/fixtures/test-fixie-config.yaml' });
    expect(client).not.toBeNull();
    expect(client!.apiKey).toBe('test-api-key');
    expect(client!.url).toBe('https://fake.api.domain');
  });
});
