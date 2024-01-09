import { FixieClientBase } from './client.js';
import { Agent, AgentId, AgentLogEntry, AgentRevision, AgentRevisionId } from './types.js';

/**
 * Base class providing access to the Fixie Agent API.
 * The 'fixie' and 'fixie-web' packages provide implementations
 * for NodeJS and web clients, respectively.
 */
export class FixieAgentBase {
  /** Use GetAgent or CreateAgent instead. */
  protected constructor(protected readonly client: FixieClientBase, protected agentMetadata: Agent) {}

  /** Return the ID for this agent. */
  public get id(): AgentId {
    return this.metadata.agentId;
  }

  /** Return the handle for this agent. */
  public get handle(): string {
    return this.metadata.handle;
  }

  public get metadata(): Agent {
    return this.agentMetadata;
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
    const metadata = await FixieAgentBase.getAgentById(client, agentId);
    return new FixieAgentBase(client, metadata);
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
    let agentList: Agent[] = [];
    let requestOffset = offset;
    while (true) {
      const requestLimit = Math.min(limit - agentList.length, 100);
      const result = (await client.requestJson(
        `/api/v1/agents?offset=${requestOffset}&limit=${requestLimit}${
          teamId !== undefined ? `&team_id=${teamId}` : ''
        } `
      )) as {
        agents: Agent[];
      };
      agentList = agentList.concat(result.agents);
      if (result.agents.length < requestLimit) {
        break;
      }
      requestOffset += requestLimit;
    }
    return agentList.map((agent: Agent) => new FixieAgentBase(client, agent));
  }

  /** Return the metadata associated with the given agent. */
  protected static async getAgentById(client: FixieClientBase, agentId: string): Promise<Agent> {
    const result = await client.requestJson(`/api/v1/agents/${agentId}`);
    return (result as any as { agent: Agent }).agent;
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
    handle,
    description,
    moreInfoUrl,
    published,
    currentRevisionId,
  }: {
    name?: string;
    handle?: string;
    description?: string;
    moreInfoUrl?: string;
    published?: boolean;
    currentRevisionId?: AgentRevisionId;
  }) {
    // `updateMask` is a string that contains the names of the non-null fields provided by the
    // caller. This is used by the server to determine which fields to update.
    const updateMask = Object.entries({ name, handle, description, moreInfoUrl, published, currentRevisionId })
      .filter(([_, y]) => y !== undefined)
      .map(([x, _]) => x)
      .join(',');
    const request = {
      agent: {
        ...this.metadata,
        ...(handle ? { handle } : {}),
        ...(name ? { displayName: name } : {}),
        ...(description ? { description } : {}),
        ...(moreInfoUrl ? { moreInfoUrl } : {}),
        ...(published !== undefined ? { published } : {}),
        ...(currentRevisionId ? { currentRevisionId } : {}),
      },
      updateMask,
    };
    const result = (await this.client.requestJson(`/api/v1/agents/${this.metadata.agentId}`, request, 'PUT')) as {
      agent: Agent;
    };
    this.agentMetadata = result.agent;
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
  public async getRevision(revisionId: AgentRevisionId): Promise<AgentRevision | null> {
    const result = (await this.client.requestJson(
      `/api/v1/agents/${this.metadata.agentId}/revisions/${revisionId}`
    )) as { revision: AgentRevision };
    return result.revision;
  }

  /** Get the current agent revision. */
  public getCurrentRevision(): Promise<AgentRevision | null> {
    if (!this.metadata.currentRevisionId) {
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
      `/api/v1/agents/${this.metadata.agentId}/revisions?offset=${offset}&limit=${limit}`
    )) as {
      revisions: AgentRevision[];
    };
    return revisionList.revisions;
  }

  /**
   * Create a new agent revision. This code only supports creating an
   * agent revision from an external URL or using the Default Agent Runtime.
   * If you need to support custom runtimes, please use the `FixieAgent`
   * class from the `fixie` package.
   *
   * @param defaultRuntimeParameters The default runtime parameters for the agent.
   * @param externalUrl The URL of the agent's external deployment, if any.
   * @param runtimeParametersSchema The JSON-encoded schema for the agent's runtime parameters.
   *  May only be specified if `externalUrl` is also specified.
   * @param isCurrent Whether this revision should be the current revision.
   *
   * @returns The newly created agent revision.
   */
  public async createRevision({
    defaultRuntimeParameters,
    externalUrl,
    runtimeParametersSchema,
    isCurrent = true,
  }: {
    defaultRuntimeParameters?: Record<string, unknown>;
    externalUrl?: string;
    runtimeParametersSchema?: string;
    isCurrent?: boolean;
  }): Promise<AgentRevision> {
    if (externalUrl === undefined && defaultRuntimeParameters === undefined) {
      throw new Error('Must specify either externalUrl or defaultRuntimeParameters');
    }

    if (runtimeParametersSchema && externalUrl === undefined) {
      throw new Error('runtimeParametersSchema is only supported for external deployments');
    }
    let externalDeployment = undefined;
    if (externalUrl !== undefined) {
      externalDeployment = {
        url: externalUrl,
        runtimeParametersSchema,
      };
    }
    const result = (await this.client.requestJson(`/api/v1/agents/${this.metadata.agentId}/revisions`, {
      revision: {
        isCurrent,
        deployment: {
          external: externalDeployment,
        },
        // The API expects this field to be pre-JSON-encoded.
        defaultRuntimeParameters: JSON.stringify(defaultRuntimeParameters),
      },
    })) as { revision: AgentRevision };
    return result.revision;
  }

  /** Set the current agent revision. */
  public setCurrentRevision(revisionId: string) {
    this.update({ currentRevisionId: revisionId });
  }

  public deleteRevision(revisionId: string): Promise<void> {
    return this.client.requestJson(
      `/api/v1/agents/${this.metadata.agentId}/revisions/${revisionId}`,
      undefined,
      'DELETE'
    );
  }
}
