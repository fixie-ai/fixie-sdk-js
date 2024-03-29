/** Unit tests for agent.ts. */

import fs from 'fs';
import { jest, afterEach, beforeEach, describe, expect, it } from '@jest/globals';
import { FixieAgent } from '../src/agent';
import { FixieClient } from '../src/client';

/** This function mocks out 'fetch' to return the given response. */
const mockFetch = (response: any) => {
  const mock = jest
    .fn<typeof global.fetch>()
    .mockImplementation((_input: RequestInfo | URL, _init?: RequestInit | undefined) => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => response,
      } as Response);
    });
  global.fetch = mock;
  return mock;
};

describe('FixieAgent config file tests', () => {
  it('LoadConfig reads agent config', async () => {
    const config = FixieAgent.LoadConfig('tests/fixtures/test-agent');
    expect(config.handle).toBe('test-agent');
    expect(config.description).toBe('Test agent description');
    expect(config.moreInfoUrl).toBe('http://fake.url.com/');
  });
  it('LoadConfig ignores unknown fields', async () => {
    const config = FixieAgent.LoadConfig('tests/fixtures/test-agent-ignore-fields');
    expect(config.handle).toBe('test-agent');
    expect(config.description).toBe('Test agent description');
    expect(config.moreInfoUrl).toBe('http://fake.url.com/');
  });
});

describe('FixieAgent AgentRevision tests', () => {
  let agent: FixieAgent;

  beforeEach(() => {
    // Create a fake Agent.
    const client = new FixieClient({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
        currentRevisionId: 'initial-revision-id',
      },
    });
    return FixieAgent.GetAgent({ client, agentId: 'fake-agent-id' }).then((a) => {
      agent = a;
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('createManagedRevision accepts tarball', async () => {
    const tarball = 'tests/fixtures/test-tarball.tar.gz';
    const tarballData = fs.readFileSync(fs.realpathSync(tarball));
    const codePackage = tarballData.toString('base64');

    const mock = mockFetch({
      revision: {
        agentId: 'fake-agent-id',
        revisionId: 'new-revision-id',
        created: '2021-08-31T18:00:00.000Z',
        isCurrent: true,
      },
    });
    const revision = await agent.createManagedRevision({
      defaultRuntimeParameters: { foo: 'bar' },
      tarball,
      environmentVariables: { TEST_ENV_VAR: 'test env var value' },
      runtimeParametersSchema: { type: 'object' },
    });
    expect(mock.mock.calls[0][0].toString()).toStrictEqual(
      'https://fake.api.fixie.ai/api/v1/agents/fake-agent-id/revisions'
    );
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('POST');
    expect(mock.mock.calls[0][1]?.body).toStrictEqual(
      JSON.stringify({
        revision: {
          isCurrent: true,
          runtime: {
            parametersSchema: { type: 'object' },
          },
          deployment: {
            managed: {
              codePackage,
              environmentVariables: { TEST_ENV_VAR: 'test env var value' },
            },
          },
          defaultRuntimeParameters: { foo: 'bar' },
        },
      })
    );
    expect(revision?.agentId).toBe('fake-agent-id');
    expect(revision?.revisionId).toBe('new-revision-id');
    expect(revision?.created).toBe('2021-08-31T18:00:00.000Z');
    expect(revision?.isCurrent).toBe(true);
  });

  it('createManagedRevision with missing tarball throws', async () => {
    expect(
      async () =>
        await agent.createManagedRevision({
          defaultRuntimeParameters: { foo: 'bar' },
          tarball: 'bogus-tarball-filename',
          environmentVariables: { TEST_ENV_VAR: 'test env var value' },
          runtimeParametersSchema: { type: 'object' },
        })
    ).rejects.toThrow();
  });
});
