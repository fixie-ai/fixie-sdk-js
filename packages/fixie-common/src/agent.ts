import { FixieClientBase } from './client.js';
import { Agent, AgentId, AgentLogEntry, AgentRevision, AgentRevisionId } from './types.js';

/**
 * Base class providing access to the Fixie Agent API.
 * The 'fixie' and 'fixie-web' packages provide implementations
 * for NodeJS and web clients, respectively.
 */
export class FixieAgentBase {
  /** Use GetAgent or CreateAgent instead. */
  protected constructor(
    protected readonly client: FixieClientBase,
    public metadata: Agent,
  ) {}

  /** Return the ID for this agent. */
  public get id(): AgentId {
    return this.metadata.agentId;
  }

  /** Return the handle for this agent. */
  public get handle(): string {
    return this.metadata.handle;
  }

  /** Return the URL for this agent's page on Fixie. */
  public agentUrl(baseUrl?: string): string {
    const url = new URL(`agents/${this.metadata.agentId}`, baseUrl ?? 'https://api.fixie.ai');
    // If using the default API host, change it to the console host.
    if (url.hostname === 'api.fixie.ai') {
      url.hostname = 'console.fixie.ai';
    }
    return url.toString();
  }

  /** Get the agent with the given ID. */
  public static async GetAgent({
    client,
    agentId,
  }: {
    client: FixieClientBase;
    agentId: AgentId;
  }): Promise<FixieAgentBase> {
    const agent = await FixieAgentBase.getAgentById(client, agentId);
    return new FixieAgentBase(client, agent);
  }

  /** List agents. */
  public static async ListAgents({
    client,
    teamId,
    offset = 0,
    limit = 1000,
  }: {
    client: FixieClientBase;
    teamId?: string;
    offset?: number;
    limit?: number;
  }): Promise<FixieAgentBase[]> {
    const agentList: Agent[] = [];
    let requestOffset = offset;
    while (true) {
      const requestLimit = Math.min(limit - agentList.length, 100);
      const result = (await client.requestJson(
        `/api/v1/agents?offset=${requestOffset}&limit=${requestLimit}${
          teamId !== undefined ? `&team_id=${teamId}` : ''
        } `,
      )) as {
        agents: Agent[];
      };
      console.log('RESULT');
      console.log(result.agents);
      agentList.concat(result.agents);
      console.log('AGENT LIST');
      console.log(agentList);
      if (result.agents.length < requestLimit) {
        break;
      }
      requestOffset += requestLimit;
    }
    console.log('AGENT LIST');
    console.log(agentList);
    return agentList.map((agent: Agent) => new FixieAgentBase(client, agent));
  }

  /** Return the metadata associated with the given agent. */
  private static getAgentById(client: FixieClientBase, agentId: string): Promise<Agent> {
    return client.requestJson(`/api/v1/agents/${agentId}`) as Promise<Agent>;
  }

  public static async CreateAgent({
    client,
    handle,
    teamId,
    name,
    description,
    moreInfoUrl,
    published,
  }: {
    client: FixieClientBase;
    handle: string;
    teamId?: string;
    name?: string;
    description?: string;
    moreInfoUrl?: string;
    published?: boolean;
  }): Promise<FixieAgentBase> {
    const agent = (await client.requestJson('/api/v1/agents', {
      agent: {
        handle,
        displayName: name,
        description,
        moreInfoUrl,
        published,
      },
      teamId,
    })) as { agent: Agent };
    return new FixieAgentBase(client, agent.agent);
  }

  /** Delete this agent. */
  delete() {
    return this.client.requestJson(`/api/v1/agents/${this.metadata.agentId}`, undefined, 'DELETE');
  }

  /** Update this agent. */
  async update({
    name,
    description,
    moreInfoUrl,
    published,
    currentRevisionId,
  }: {
    name?: string;
    description?: string;
    moreInfoUrl?: string;
    published?: boolean;
    currentRevisionId?: AgentRevisionId;
  }) {
    // `updateMask` is a string that contains the names of the non-null fields provided by the
    // caller. This is used by the server to determine which fields to update.
    const updateMask = Object.entries({ name, description, moreInfoUrl, published, currentRevisionId })
      .filter(([_, y]) => y !== undefined)
      .map(([x, _]) => x)
      .join(',');
    const request = {
      agent: {
        ...this.metadata,
        displayName: name,
        description,
        moreInfoUrl,
        published,
        currentRevisionId,
      },
      updateMask,
    };
    const result = (await this.client.requestJson(`/api/v1/agents/${this.metadata.agentId}`, request, 'PUT')) as {
      agent: Agent;
    };
    this.metadata = result.agent;
  }

  /** Return logs for this Agent. */
  async getLogs({
    start,
    end,
    limit,
    offset,
    minSeverity,
    conversationId,
    messageId,
  }: {
    start?: Date;
    end?: Date;
    limit?: number;
    offset?: number;
    minSeverity?: number;
    conversationId?: string;
    messageId?: string;
  }): Promise<AgentLogEntry[]> {
    // We don't actually care about the full URL here. We're only using the
    // URL to build up the query parameters.
    const url = new URL('http://localhost/');
    if (start) {
      url.searchParams.append('startTimestamp', Math.floor(start.getTime() / 1000).toString());
    }
    if (end) {
      url.searchParams.append('endTimestamp', Math.floor(end.getTime() / 1000).toString());
    }
    if (limit) {
      url.searchParams.append('limit', limit.toString());
    }
    if (offset) {
      url.searchParams.append('offset', offset.toString());
    }
    if (minSeverity) {
      url.searchParams.append('minSeverity', minSeverity.toString());
    }
    if (conversationId) {
      url.searchParams.append('conversationId', conversationId);
    }
    if (messageId) {
      url.searchParams.append('messageId', messageId);
    }
    const retval = await this.client.request(`/api/v1/agents/${this.metadata.agentId}/logs${url.search}`);
    if (retval.status !== 200) {
      return [];
    }
    const logs = (await retval.json()) as { logs: AgentLogEntry[] };
    return logs.logs;
  }

  /** Get the specified agent revision. */
  public getRevision(revisionId: AgentRevisionId): Promise<AgentRevision | null> {
    return this.client.requestJson(
      `/api/v1/agents/${this.metadata.agentId}/revisions/${revisionId}`,
    ) as Promise<AgentRevision>;
  }

  /** Get the current agent revision. */
  public getCurrentRevision(): Promise<AgentRevision | null> {
    if (this.metadata.currentRevisionId === undefined) {
      return Promise.resolve(null);
    }
    return this.getRevision(this.metadata.currentRevisionId);
  }

  /** List agent revisions. */
  public async listAgentRevisions({
    offset = 0,
    limit = 100,
  }: {
    offset?: number;
    limit?: number;
  }): Promise<AgentRevision[]> {
    const revisionList = (await this.client.requestJson(
      `/api/v1/agents/${this.metadata.agentId}/revisions?offset=${offset}&limit=${limit}`,
    )) as {
      revisions: AgentRevision[];
    };
    return revisionList.revisions;
  }

  /** Set the current agent revision. */
  public setCurrentRevision(revisionId: string) {
    this.update({ currentRevisionId: revisionId });
  }

  public deleteRevision(revisionId: string): Promise<void> {
    return this.client.requestJson(
      `/api/v1/agents/${this.metadata.agentId}/revisions/${revisionId}`,
      undefined,
      'DELETE',
    );
  }
}
