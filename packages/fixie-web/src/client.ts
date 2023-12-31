import { FixieClientBase, AgentId, ConversationId } from 'fixie-common';
import { VoiceSession, VoiceSessionInit } from './voice.js';

/**
 * A client to the Fixie AI platform.
 *
 * This client is intended for use in web clients only. For NodeJS
 * applications, use the 'fixie' package.
 */
export class FixieClient extends FixieClientBase {
  /**
   * Create a new voice session.
   *
   * @param options.agentId The ID of the agent to start a conversation with.
   * @param options.conversationId The ID of an existing conversation to attach to.
   * @param options.init Various configuration parameters for the voice session.
   */
  createVoiceSession({
    agentId,
    conversationId,
    init,
  }: {
    agentId: AgentId;
    conversationId?: ConversationId;
    init?: VoiceSessionInit;
  }) {
    return new VoiceSession(agentId, conversationId, init);
  }
}
