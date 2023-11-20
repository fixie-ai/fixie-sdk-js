/** Unit tests for client.ts. */

import { jest, beforeEach, afterEach, describe, expect, it } from '@jest/globals';
import { FixieClientBase } from '../src/client';
import { FixieAgentBase } from '../src/agent';

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

describe('FixieAgentBase Agent tests', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('GetAgent works', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    const mock = mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
      },
    });
    const agent = await FixieAgentBase.GetAgent({ client, agentId: 'fake-agent-id' });
    expect(mock.mock.calls[0][0].toString()).toStrictEqual('https://fake.api.fixie.ai/api/v1/agents/fake-agent-id');
    expect(agent.id).toBe('fake-agent-id');
    expect(agent.handle).toBe('fake-agent-handle');
    expect(agent.agentUrl()).toBe('https://console.fixie.ai/agents/fake-agent-id');
  });

  it('ListAgents works', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    const mock = mockFetch({
      agents: [
        {
          agentId: 'fake-agent-id-1',
          handle: 'fake-agent-handle-1',
        },
        {
          agentId: 'fake-agent-id-2',
          handle: 'fake-agent-handle-2',
        },
        {
          agentId: 'fake-agent-id-3',
          handle: 'fake-agent-handle-3',
        },
        {
          agentId: 'fake-agent-id-4',
          handle: 'fake-agent-handle-4',
        },
      ],
    });
    const agents = await FixieAgentBase.ListAgents({ client });
    expect(mock.mock.calls[0][0].toString()).toStrictEqual(
      'https://fake.api.fixie.ai/api/v1/agents?offset=0&limit=100'
    );
    expect(agents.length).toBe(4);
    expect(agents[0].id).toBe('fake-agent-id-1');
    expect(agents[0].handle).toBe('fake-agent-handle-1');
    expect(agents[0].agentUrl()).toBe('https://console.fixie.ai/agents/fake-agent-id-1');
  });

  it('CreateAgent works', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    const mock = mockFetch({
      agent: {
        displayName: 'Test agent',
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
      },
    });
    const agent = await FixieAgentBase.CreateAgent({ client, handle: 'fake-agent-handle' });
    expect(mock.mock.calls[0][0].toString()).toStrictEqual('https://fake.api.fixie.ai/api/v1/agents');
    expect(agent.id).toBe('fake-agent-id');
    expect(agent.metadata.displayName).toBe('Test agent');
    expect(agent.handle).toBe('fake-agent-handle');
    expect(agent.agentUrl()).toBe('https://console.fixie.ai/agents/fake-agent-id');
  });

  it('agent.delete() works', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
      },
    });
    const agent = await FixieAgentBase.GetAgent({ client, agentId: 'fake-agent-id' });
    expect(agent.id).toBe('fake-agent-id');
    const mock = mockFetch({});
    agent.delete();
    expect(mock.mock.calls[0][0].toString()).toStrictEqual('https://fake.api.fixie.ai/api/v1/agents/fake-agent-id');
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('DELETE');
  });

  it('agent.update() works', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
        moreInfoUrl: 'https://fake.url',
      },
    });
    const agent = await FixieAgentBase.GetAgent({ client, agentId: 'fake-agent-id' });
    expect(agent.id).toBe('fake-agent-id');
    expect(agent.handle).toBe('fake-agent-handle');
    expect(agent.metadata.moreInfoUrl).toBe('https://fake.url');
    const mock = mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
        description: 'Test agent description',
        moreInfoUrl: 'https://fake.url.2',
      },
    });
    agent.update({ description: 'Test agent description', moreInfoUrl: 'https://fake.url.2' });
    expect(mock.mock.calls[0][0].toString()).toStrictEqual('https://fake.api.fixie.ai/api/v1/agents/fake-agent-id');
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('PUT');
    expect(mock.mock.calls[0][1]?.body).toStrictEqual(
      JSON.stringify({
        agent: {
          agentId: 'fake-agent-id',
          handle: 'fake-agent-handle',
          moreInfoUrl: 'https://fake.url.2',
          description: 'Test agent description',
        },
        updateMask: 'description,moreInfoUrl',
      })
    );
    expect(agent.id).toBe('fake-agent-id');
  });
});

describe('FixieAgentBase logs tests', () => {
  let agent: FixieAgentBase;

  beforeEach(() => {
    // Create a fake Agent.
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
      },
    });
    return FixieAgentBase.GetAgent({ client, agentId: 'fake-agent-id' }).then((a) => {
      agent = a;
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('getLogs works', async () => {
    const mock = mockFetch({
      logs: [
        {
          timestamp: '2021-08-31T18:00:00.000Z',
          message: 'This is a log message',
        },
      ],
    });
    const logs = await agent.getLogs({});
    expect(mock.mock.calls[0][0].toString()).toStrictEqual(
      'https://fake.api.fixie.ai/api/v1/agents/fake-agent-id/logs'
    );
    expect(logs.length).toBe(1);
    expect(logs[0].timestamp).toBe('2021-08-31T18:00:00.000Z');
    expect(logs[0].message).toBe('This is a log message');
  });
});

describe('FixieAgentBase AgentRevision tests', () => {
  let agent: FixieAgentBase;

  beforeEach(() => {
    // Create a fake Agent.
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
        currentRevisionId: 'initial-revision-id',
      },
    });
    return FixieAgentBase.GetAgent({ client, agentId: 'fake-agent-id' }).then((a) => {
      agent = a;
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('getRevision works', async () => {
    const mock = mockFetch({
      revision: {
        agentId: 'fake-agent-id',
        revisionId: 'fake-revision-id',
        created: '2021-08-31T18:00:00.000Z',
        isCurrent: true,
        defaultRuntimeParameters: '{"foo": "bar"}',
        deployment: {
          external: {
            url: 'https://fake.url',
          },
        },
      },
    });
    const revision = await agent.getRevision('fake-revision-id');
    expect(mock.mock.calls[0][0].toString()).toStrictEqual(
      'https://fake.api.fixie.ai/api/v1/agents/fake-agent-id/revisions/fake-revision-id'
    );
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('GET');
    expect(revision?.agentId).toBe('fake-agent-id');
    expect(revision?.revisionId).toBe('fake-revision-id');
    expect(revision?.created).toBe('2021-08-31T18:00:00.000Z');
    expect(revision?.isCurrent).toBe(true);
    expect(revision?.defaultRuntimeParameters).toBe('{"foo": "bar"}');
    expect(revision?.deployment?.external?.url).toBe('https://fake.url');
  });

  it('getCurrentRevision works', async () => {
    const mock = mockFetch({
      revision: {
        agentId: 'fake-agent-id',
        revisionId: 'initial-revision-id',
        created: '2021-08-31T18:00:00.000Z',
        isCurrent: true,
      },
    });
    const revision = await agent.getCurrentRevision();
    expect(mock.mock.calls[0][0].toString()).toStrictEqual(
      'https://fake.api.fixie.ai/api/v1/agents/fake-agent-id/revisions/initial-revision-id'
    );
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('GET');
    expect(revision?.agentId).toBe('fake-agent-id');
    expect(revision?.revisionId).toBe('initial-revision-id');
    expect(revision?.created).toBe('2021-08-31T18:00:00.000Z');
    expect(revision?.isCurrent).toBe(true);
  });

  it('getCurrentRevision returns null for undefined currentRevision', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
        currentRevisionId: undefined,
      },
    });
    const agent = await FixieAgentBase.GetAgent({ client, agentId: 'fake-agent-id' });
    const revision = await agent.getCurrentRevision();
    expect(revision).toBe(null);
  });

  it('getCurrentRevision returns null for null currentRevision', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
        currentRevisionId: null,
      },
    });
    const agent = await FixieAgentBase.GetAgent({ client, agentId: 'fake-agent-id' });
    const revision = await agent.getCurrentRevision();
    expect(revision).toBe(null);
  });

  it('getCurrentRevision returns null for empty currentRevision', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
        currentRevisionId: '',
      },
    });
    const agent = await FixieAgentBase.GetAgent({ client, agentId: 'fake-agent-id' });
    const revision = await agent.getCurrentRevision();
    expect(revision).toBe(null);
  });

  it('setCurrentRevision works', async () => {
    expect(agent.metadata.currentRevisionId).toBe('initial-revision-id');
    const mock = mockFetch({});
    agent.setCurrentRevision('second-revision-id');
    expect(mock.mock.calls[0][0].toString()).toStrictEqual('https://fake.api.fixie.ai/api/v1/agents/fake-agent-id');
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('PUT');
    expect(mock.mock.calls[0][1]?.body).toStrictEqual(
      JSON.stringify({
        agent: {
          agentId: 'fake-agent-id',
          handle: 'fake-agent-handle',
          currentRevisionId: 'second-revision-id',
        },
        updateMask: 'currentRevisionId',
      })
    );
  });

  it('deleteRevision works', async () => {
    const mock = mockFetch({});
    agent.deleteRevision('fake-revision-id');
    expect(mock.mock.calls[0][0].toString()).toStrictEqual(
      'https://fake.api.fixie.ai/api/v1/agents/fake-agent-id/revisions/fake-revision-id'
    );
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('DELETE');
  });

  it('createRevision works', async () => {
    const mock = mockFetch({
      revision: {
        agentId: 'fake-agent-id',
        revisionId: 'new-revision-id',
        created: '2021-08-31T18:00:00.000Z',
        isCurrent: true,
        runtime: {
          parametersSchema: '{"type":"object"}',
        },
      },
    });
    const revision = await agent.createRevision({
      defaultRuntimeParameters: { foo: 'bar' },
      externalUrl: 'https://fake.url',
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
          deployment: {
            external: {
              url: 'https://fake.url',
            },
          },
          runtime: {
            parametersSchema: '{"type":"object"}',
          },
          defaultRuntimeParameters: '{"foo":"bar"}',
        },
      })
    );
    expect(revision?.agentId).toBe('fake-agent-id');
    expect(revision?.revisionId).toBe('new-revision-id');
    expect(revision?.created).toBe('2021-08-31T18:00:00.000Z');
    expect(revision?.isCurrent).toBe(true);
  });

  it('createRevision requires either externalUrl or defaultRuntimeParameters', async () => {
    expect(async () => await agent.createRevision({})).rejects.toThrow();
  });

  it('createRevision with runtimeParametersSchema requires externalUrl', async () => {
    expect(async () => await agent.createRevision({ runtimeParametersSchema: {} })).rejects.toThrow();
  });
});
