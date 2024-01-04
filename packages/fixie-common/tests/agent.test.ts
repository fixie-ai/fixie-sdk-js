/** Unit tests for client.ts. */

import { jest, afterEach, describe, expect, it } from '@jest/globals';
import { FixieClientBase } from '../src/client';
import { FixieAgentBase } from '../src/agent';

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

describe('FixieAgentBase tests', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });
  it('GetAgent works', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
      },
    });
    const agent = await FixieAgentBase.GetAgent({ client, agentId: 'fake-agent-id' });
    expect(agent.id).toBe('fake-agent-id');
    expect(agent.handle).toBe('fake-agent-handle');
    expect(agent.agentUrl()).toBe('https://console.fixie.ai/agents/fake-agent-id');
  });
  it('ListAgents works', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
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
    expect(agents.length).toBe(4);
    expect(agents[0].id).toBe('fake-agent-id-1');
    expect(agents[0].handle).toBe('fake-agent-handle-1');
    expect(agents[0].agentUrl()).toBe('https://console.fixie.ai/agents/fake-agent-id-1');
  });
  it('CreateAgent works', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
      agent: {
        agentId: 'fake-agent-id',
        handle: 'fake-agent-handle',
      },
    });
    const agent = await FixieAgentBase.CreateAgent({ client, handle: 'fake-agent-handle' });
    expect(agent.id).toBe('fake-agent-id');
    expect(agent.handle).toBe('fake-agent-handle');
    expect(agent.agentUrl()).toBe('https://console.fixie.ai/agents/fake-agent-id');
  });
});
