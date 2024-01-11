/** This file defines types exposed by the Fixie Platform API. */

// TODO: Autogenerate this from our proto or OpenAPI specs.

import { Jsonifiable } from 'type-fest';

/** Represents metadata about a single user. */
export interface User {
  userId: string;
  email: string;
  fullName?: string;
  avatarUrl?: string;
  created: Date;
  modified: Date;
  apiToken?: string;
  lastLogin: Date;
}

/** Represents a user's role on a team. */
export interface MembershipRole {
  isAdmin: boolean;
}

/** Represents a user's membership on a team. */
export interface Membership {
  teamId: string;
  user: User;
  role: MembershipRole;
  pending: boolean;
  created: Date;
  modified: Date;
}

/** Represents a team. */
export interface Team {
  teamId: string;
  displayName?: string;
  description?: string;
  avatarUrl?: string;
  members: Membership[];
  created: Date;
  modified: Date;
}

/** Represents an owner of an object, which can be a User or a Team. */
export interface Principal {
  user?: User;
  team?: Team;
}

/** Represents an agent ID. */
export type AgentId = string;

/** Represents an agent revision ID. */
export type AgentRevisionId = string;

/** Represents metadata about an agent managed by the Fixie service. */
export interface Agent {
  agentId: AgentId;
  owner: Principal;
  handle: string;
  displayName?: string;
  description?: string;
  moreInfoUrl?: string;
  created: Date;
  currentRevisionId?: AgentRevisionId;
  modified: Date;
  published?: boolean;
  branded?: boolean;
}

/** Represents metadata about an agent revision. */
export interface AgentRevision {
  agentId: AgentId;
  revisionId: AgentRevisionId;
  created: Date;
  isCurrent: boolean;
  defaultRuntimeParameters?: string;
  runtime?: AgentRuntime;
  deployment?: AgentDeployment;
}

/** Agent runtime parameters. */
export interface AgentRuntime {
  parametersSchema: string;
}

/** Agent deployment settings. */
export interface AgentDeployment {
  external?: ExternalDeployment;
  managed?: ManagedDeployment;
}

/** Represents an externally-hosted Agent. */
export interface ExternalDeployment {
  url: string;
}

/** Represents a Fixie-managed Agent. */
export interface ManagedDeployment {
  environmentVariables?: Record<string, string>;
  codePackage?: string;
}

/** Represents an Agent Log entry. */
export interface AgentLogEntry {
  timestamp: Date;
  traceId?: string;
  spanId?: string;
  severity?: number;
  message?: string;
}

/** Represents a pending invitation for a user to join a team. */
export interface Invitation {
  inviteCode: string;
  sender: string;
  email: string;
  teamName: string;
  role: MembershipRole;
  created: Date;
}

/** Represents a conversation ID. */
export type ConversationId = string;

/** Represents a Metadata field. */
export type Metadata = Record<string, Jsonifiable | undefined>;

export interface BaseConversationTurn<Role extends string> {
  role: Role;
  timestamp: string;
  id: string;

  /**
   * Any metadata the client or server would like to attach to the message.
   * For instance, the client might include UI state from the host app,
   * or the server might include debugging info.
   */
  metadata?: Jsonifiable;

  state: State;
}

export interface Conversation {
  id: ConversationId;
  turns: ConversationTurn[];
}

export interface UserOrAssistantConversationTurn<Role extends string> extends BaseConversationTurn<Role> {
  messages: Message[];
}

/**
 * Whether the message is being generated, complete, or resulted in an error.
 *
 * When the user is typing or the AI is generating tokens, this will be 'in-progress'.
 *
 * If the backend produces an error while trying to make a response, this will be an Error object.
 *
 * If the user requests that the AI stop generating a message, the state will be 'stopped'.
 */
type State = 'in-progress' | 'done' | 'stopped' | 'error';
export interface StateFields {
  state: State;
  errorDetail?: string;
}

export interface AssistantConversationTurn extends UserOrAssistantConversationTurn<'assistant'>, StateFields {
  /**
   * The user turn that this turn was a reply to.
   */
  inReplyToId?: string;
}

export interface UserConversationTurn extends UserOrAssistantConversationTurn<'user'> {}

export type ConversationTurn = AssistantConversationTurn | UserConversationTurn;

/** A message in the conversation. */
export interface BaseMessage {
  /** Any metadata the client or server would like to attach to the message.
      For instance, the client might include UI state from the host app,
      or the server might include debugging info.
  */
  metadata?: Jsonifiable;
}

export interface FunctionCall extends BaseMessage {
  kind: 'functionCall';
  name?: string;
  args?: Record<string, string | number | boolean | null>;
}

export interface FunctionResponse extends BaseMessage {
  kind: 'functionResponse';
  name: string;
  response: string;
  failed?: boolean;
}

export interface TextMessage extends BaseMessage {
  kind: 'text';
  /** The text content of the message. */
  content: string;
}

export type Message = FunctionCall | FunctionResponse | TextMessage;
