import { gql } from '@apollo/client/core/index.js';
import { FixieClientBase } from './client.js';

/** Represents metadata about an agent managed by the Fixie service. */
export interface AgentMetadata {
  uuid: string;
  handle: string;
  name?: string;
  description?: string;
  moreInfoUrl?: string;
  published?: boolean;
  created: Date;
  modified: Date;
  currentRevision?: AgentRevision;
  allRevisions?: AgentRevision[];
}

/** Represents metadata about an agent revision. */
export interface AgentRevision {
  id: string;
  created: Date;
  isCurrent: boolean;
}

/** Represents an Agent Log entry. */
export interface AgentLogEntry {
  timestamp: Date;
  traceId?: string;
  spanId?: string;
  severity?: number;
  message?: string;
}

/**
 * Base class providing access to the Fixie Agent API.
 * The 'fixie' and 'fixie-web' packages provide implementations
 * for NodeJS and web clients, respectively.
 */
export class FixieAgentBase {
  /** Use GetAgent or CreateAgent instead. */
  protected constructor(protected readonly client: FixieClientBase, public metadata: AgentMetadata) {}

  /** Return the handle for this agent. */
  public get handle(): string {
    return this.metadata.handle;
  }

  /** Return the URL for this agent's page on Fixie. */
  public agentUrl(baseUrl?: string): string {
    const url = new URL(`agents/${this.metadata.uuid}`, baseUrl ?? 'https://api.fixie.ai');
    // If using the default API host, change it to the console host.
    if (url.hostname === 'api.fixie.ai') {
      url.hostname = 'console.fixie.ai';
    }
    return url.toString();
  }

  /** Get the agent with the given agent ID or handle. */
  public static async GetAgent({
    client,
    agentId,
    handle,
  }: {
    client: FixieClientBase;
    agentId?: string;
    handle?: string;
  }): Promise<FixieAgentBase> {
    if (!agentId && !handle) {
      throw new Error('Must specify either agentId or handle');
    }
    if (agentId && handle) {
      throw new Error('Must specify either agentId or handle, not both');
    }
    let metadata: AgentMetadata;
    if (agentId) {
      metadata = await FixieAgentBase.getAgentById(client, agentId);
    } else {
      metadata = await FixieAgentBase.getAgentByHandle(client, handle!);
    }
    return new FixieAgentBase(client, metadata);
  }

  /** Return all agents visible to the user. */
  public static async ListAgents(client: FixieClientBase): Promise<FixieAgentBase[]> {
    const result = await client.gqlClient().query({
      fetchPolicy: 'no-cache',
      query: gql`
        {
          allAgentsForUser {
            uuid
          }
        }
      `,
    });
    return Promise.all(
      result.data.allAgentsForUser.map((agent: any) => this.GetAgent({ client, agentId: agent.uuid }))
    );
  }

  /** Return the metadata associated with the given agent. */
  private static async getAgentById(client: FixieClientBase, agentId: string): Promise<AgentMetadata> {
    const result = await client.gqlClient().query({
      fetchPolicy: 'no-cache',
      query: gql`
        query GetAgentById($agentId: String!) {
          agent: agentById(agentId: $agentId) {
            agentId
            uuid
            handle
            name
            description
            moreInfoUrl
            created
            modified
            published
            currentRevision {
              id
              created
            }
            allRevisions {
              id
              created
            }
          }
        }
      `,
      variables: { agentId },
    });

    return {
      uuid: result.data.agent.uuid,
      handle: result.data.agent.handle,
      name: result.data.agent.name,
      description: result.data.agent.description,
      moreInfoUrl: result.data.agent.moreInfoUrl,
      published: result.data.agent.published,
      created: new Date(result.data.agent.created),
      modified: new Date(result.data.agent.modified),
      currentRevision: result.data.agent.currentRevision,
      allRevisions: result.data.agent.allRevisions,
    };
  }

  /** Return the metadata associated with the given agent handle. */
  private static async getAgentByHandle(client: FixieClientBase, handle: string): Promise<AgentMetadata> {
    const result = await client.gqlClient().query({
      fetchPolicy: 'no-cache',
      query: gql`
        query GetAgentByHandle($handle: String!) {
          agent: agentByHandle(handle: $handle) {
            agentId
            uuid
            handle
            name
            description
            moreInfoUrl
            created
            modified
            published
            currentRevision {
              id
              created
            }
            allRevisions {
              id
              created
            }
          }
        }
      `,
      variables: { handle },
    });

    return {
      uuid: result.data.agent.uuid,
      handle: result.data.agent.handle,
      name: result.data.agent.name,
      description: result.data.agent.description,
      moreInfoUrl: result.data.agent.moreInfoUrl,
      published: result.data.agent.published,
      created: new Date(result.data.agent.created),
      modified: new Date(result.data.agent.modified),
      currentRevision: result.data.agent.currentRevision,
      allRevisions: result.data.agent.allRevisions,
    };
  }

  /** Create a new Agent. */
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
    const result = await client.gqlClient().mutate({
      mutation: gql`
        mutation CreateAgent(
          $handle: String!
          $teamId: String
          $description: String
          $moreInfoUrl: String
          $published: Boolean
        ) {
          createAgent(
            agentData: {
              handle: $handle
              teamId: $teamId
              description: $description
              moreInfoUrl: $moreInfoUrl
              published: $published
            }
          ) {
            agent {
              uuid
            }
          }
        }
      `,
      variables: {
        handle,
        teamId,
        name,
        description,
        moreInfoUrl,
        published: published ?? true,
      },
    });
    const agentId = result.data.createAgent.agent.uuid;
    return FixieAgentBase.GetAgent({ client, agentId });
  }

  /** Delete this agent. */
  delete() {
    return this.client.gqlClient().mutate({
      mutation: gql`
        mutation DeleteAgent($uuid: UUID!) {
          deleteAgent(agentData: { uuid: $uuid }) {
            agent {
              uuid
              handle
            }
          }
        }
      `,
      variables: { uuid: this.metadata.uuid },
    });
  }

  /** Update this agent. */
  async update({
    name,
    description,
    moreInfoUrl,
    published,
  }: {
    name?: string;
    description?: string;
    moreInfoUrl?: string;
    published?: boolean;
  }) {
    await this.client.gqlClient().mutate({
      mutation: gql`
        mutation UpdateAgent(
          $uuid: UUID!
          $handle: String
          $name: String
          $description: String
          $moreInfoUrl: String
          $published: Boolean
        ) {
          updateAgent(
            agentData: {
              uuid: $uuid
              handle: $handle
              name: $name
              description: $description
              moreInfoUrl: $moreInfoUrl
              published: $published
            }
          ) {
            agent {
              uuid
            }
          }
        }
      `,
      variables: {
        uuid: this.metadata.uuid,
        handle: this.handle,
        name,
        description,
        moreInfoUrl,
        published,
      },
    });
    this.metadata = await FixieAgentBase.getAgentById(this.client, this.metadata.uuid);
  }

  /** Return logs for this Agent. Returns the last 15 minutes of agent logs. */
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
    const retval = await this.client.request(`/api/v1/agents/${this.metadata.uuid}/logs${url.search}`);
    if (retval.status !== 200) {
      return [];
    }
    const logs = (await retval.json()) as { logs: AgentLogEntry[] };
    return logs.logs;
  }

  /** Get the current agent revision. */
  public async getCurrentRevision(): Promise<AgentRevision | null> {
    const result = await this.client.gqlClient().query({
      fetchPolicy: 'no-cache',
      query: gql`
        query GetRevisionId($agentId: String!) {
          agentById(agentId: $agentId) {
            currentRevision {
              id
              created
            }
          }
        }
      `,
      variables: { agentId: this.metadata.uuid },
    });
    return result.data.agentById.currentRevision as AgentRevision;
  }

  /** Set the current agent revision. */
  public async setCurrentRevision(revisionId: string): Promise<AgentRevision> {
    const result = await this.client.gqlClient().mutate({
      mutation: gql`
        mutation SetCurrentAgentRevision($agentUuid: UUID!, $currentRevisionId: ID!) {
          updateAgent(agentData: { uuid: $agentUuid, currentRevisionId: $currentRevisionId }) {
            agent {
              currentRevision {
                id
                created
              }
            }
          }
        }
      `,
      variables: { agentUuid: this.metadata.uuid, currentRevisionId: revisionId },
      fetchPolicy: 'no-cache',
    });
    return result.data.updateAgent.agent.currentRevision as AgentRevision;
  }

  public async deleteRevision(revisionId: string): Promise<void> {
    await this.client.gqlClient().mutate({
      mutation: gql`
        mutation DeleteAgentRevision($agentUuid: UUID!, $revisionId: ID!) {
          deleteAgentRevision(agentUuid: $agentUuid, revisionId: $revisionId) {
            agent {
              agentId
            }
          }
        }
      `,
      variables: { agentUuid: this.metadata.uuid, revisionId },
      fetchPolicy: 'no-cache',
    });
  }
}
