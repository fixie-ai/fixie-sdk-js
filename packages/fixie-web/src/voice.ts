/** This file defines the Fixie Voice SDK. */

import { AgentId, ConversationId } from '@fixieai/fixie-common';
import {
  createLocalTracks,
  ConnectionState,
  DataPacket_Kind,
  LocalAudioTrack,
  RemoteAudioTrack,
  RemoteTrack,
  Room,
  RoomEvent,
  Track,
  TrackEvent,
} from 'livekit-client';

/** Represents the state of a VoiceSession. */
export enum VoiceSessionState {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  IDLE = 'idle',
  LISTENING = 'listening',
  THINKING = 'thinking',
  SPEAKING = 'speaking',
}

/** Initialization parameters for a VoiceSession. */
export interface VoiceSessionInit {
  asrProvider?: string;
  asrLanguage?: string;
  model?: string;
  ttsProvider?: string;
  ttsModel?: string;
  ttsVoice?: string;
  webrtcUrl?: string;
  recordingTemplateUrl?: string;
  roomName?: string;
}

/** Web Audio AnalyserNode for an audio stream. */
export class StreamAnalyzer {
  source: MediaStreamAudioSourceNode;
  analyzer: AnalyserNode;
  constructor(context: AudioContext, stream: MediaStream) {
    this.source = context.createMediaStreamSource(stream);
    this.analyzer = context.createAnalyser();
    this.source.connect(this.analyzer);
  }
  stop() {
    this.source.disconnect();
  }
}

export class VoiceSessionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'VoiceSessionError';
  }
}

/** Manages a single voice session with a Fixie agent. */
export class VoiceSession {
  private readonly audioContext = new AudioContext();
  private readonly audioElement = new Audio();
  private readonly textEncoder = new TextEncoder();
  private readonly textDecoder = new TextDecoder();
  private _state = VoiceSessionState.DISCONNECTED;
  private socket?: WebSocket;
  private audioStarted = false;
  private started = false;
  private room?: Room;
  private localAudioTrack?: LocalAudioTrack;
  // True when we should have entered speaking state but didn't due to analyzer not being ready.
  private delayedSpeakingState = false;
  private inAnalyzer?: StreamAnalyzer;
  private outAnalyzer?: StreamAnalyzer;
  private pinger?: ReturnType<typeof setInterval>;
  private outputTranscript: string = '';

  /** Called when this VoiceSession changes its state. */
  onStateChange?: (state: VoiceSessionState) => void;

  /** Called when the input changes. */
  onInputChange?: (text: string, final: boolean) => void;

  /** Called as output voice is played with the text that should have completed playing (for this response). */
  onOutputChange?: (text: string, final: boolean) => void;

  /** Called when new latency data is available. */
  onLatencyChange?: (metric: string, value: number) => void;

  /** Called when an error occurs. */
  onError?: (error: VoiceSessionError) => void;

  constructor(readonly agentId: AgentId, public conversationId?: ConversationId, readonly params?: VoiceSessionInit) {
    console.log('[voiceSession] creating VoiceSession');
  }

  /** Returns the current state of this VoiceSession. */
  get state(): VoiceSessionState {
    return this._state;
  }

  /** Returns an AnalyserNode that can be used to analyze the input audio signal. */
  get inputAnalyzer(): AnalyserNode | undefined {
    return this.inAnalyzer?.analyzer;
  }

  /** Returns an AnalyserNode that can be used to analyze the output audio signal. */
  get outputAnalyzer(): AnalyserNode | undefined {
    return this.outAnalyzer?.analyzer;
  }

  /** Returns the Room Name currently in use by this VoiceSession. */
  get roomName(): string | undefined {
    return this.room?.name;
  }

  /** Warm up the VoiceSession by making network connections. This is called automatically when the VoiceSession object is created. */
  warmup(): void {
    // No-op if already warming/warmed.
    if (this._state != VoiceSessionState.DISCONNECTED) {
      return;
    }
    console.log('[voiceSession] warming up');
    try {
      const url = this.params?.webrtcUrl ?? 'wss://wsapi.fixie.ai';
      this.socket = new WebSocket(url);
      this.socket.onopen = () => this.handleSocketOpen();
      this.socket.onmessage = (event) => this.handleSocketMessage(event);
      this.socket.onclose = (event) => this.handleSocketClose(event);
      this.changeState(VoiceSessionState.CONNECTING);
    } catch (e) {
      const err = e as Error;
      console.error('[voiceSession] failed to create socket', e);
      this.onError?.(new VoiceSessionError(`Failed to create socket: ${err.message}`));
    }
  }

  /** Start the audio channels associated with this VoiceSession. This will request microphone permissions from the user. */
  async startAudio() {
    console.log('[voiceSession] startAudio');
    this.audioContext.resume();
    this.audioElement.play();
    const localTracks = await createLocalTracks({ audio: true, video: false });
    this.localAudioTrack = localTracks[0] as LocalAudioTrack;
    console.log('[voiceSession] got mic stream');
    this.inAnalyzer = new StreamAnalyzer(this.audioContext, this.localAudioTrack!.mediaStream!);
    this.audioStarted = true;
  }

  /** Start this VoiceSession. This will call startAudio if it has not been called yet.*/
  async start() {
    this.warmup();
    console.log('[voiceSession] starting');
    if (this.started) {
      console.warn('[voiceSession - start] Already started!');
      return;
    }
    if (!this.audioStarted) {
      await this.startAudio();
    }
    this.started = true;
    this.maybePublishLocalAudio();
  }

  /** Stop this VoiceSession. */
  async stop() {
    console.log('[voiceSession] stopping');
    clearInterval(this.pinger);
    this.pinger = undefined;
    await this.room?.disconnect();
    this.room = undefined;
    this.inAnalyzer?.stop();
    this.outAnalyzer?.stop();
    this.inAnalyzer = undefined;
    this.outAnalyzer = undefined;
    this.localAudioTrack?.stop();
    this.localAudioTrack = undefined;
    this.socket?.close();
    this.socket = undefined;
    this.audioStarted = false;
    this.started = false;
    this.changeState(VoiceSessionState.DISCONNECTED);
  }

  /** Interrupt this VoiceSession. */
  interrupt() {
    console.log('[voiceSession] interrupting');
    if (!this.started) {
      console.warn('[voiceSession - interrupt] Not started!');
      return;
    }
    const obj = { type: 'interrupt' };
    this.sendData(obj);
  }

  /** Send a message via text. Must be in LISTENING state. */
  sendText(text: string) {
    if (this._state != VoiceSessionState.LISTENING) {
      console.warn('[voiceSession - sendText] Not in LISTENING state!');
      return;
    }
    const obj = { type: 'input_text_message', text };
    this.sendData(obj);
  }

  private changeState(state: VoiceSessionState) {
    if (state != this._state) {
      console.log(`[voiceSession] ${this._state} -> ${state}`);
      this._state = state;
      this.audioElement.muted = state != VoiceSessionState.SPEAKING;
      this.onStateChange?.(state);
    }
  }

  private startPinger() {
    this.pinger = setInterval(() => {
      const obj = { type: 'ping', timestamp: performance.now() };
      this.sendData(obj);
    }, 5000);
  }

  private maybePublishLocalAudio() {
    if (this.started && this.room && this.room.state === ConnectionState.Connected && this.localAudioTrack) {
      console.log('[voiceSession] publishing local audio track');
      const opts = { name: 'audio', simulcast: false, source: Track.Source.Microphone };
      this.room.localParticipant.publishTrack(this.localAudioTrack, opts);
      this.changeState(VoiceSessionState.IDLE);
    } else {
      console.log(
        `[voiceSession] not publishing local audio track - room state is ${this.room?.state}, local audio is ${
          this.localAudioTrack != null
        }`
      );
    }
  }

  private sendData(obj: any) {
    this.room?.localParticipant.publishData(this.textEncoder.encode(JSON.stringify(obj)), DataPacket_Kind.RELIABLE);
  }

  private handleSocketOpen() {
    console.log('[voiceSession] socket opened');
    this.changeState(VoiceSessionState.CONNECTED);
    const obj = {
      type: 'init',
      params: {
        asr: {
          provider: this.params?.asrProvider,
          language: this.params?.asrLanguage,
        },
        tts: {
          provider: this.params?.ttsProvider,
          model: this.params?.ttsModel,
          voice: this.params?.ttsVoice,
        },
        agent: {
          agentId: this.agentId,
          conversationId: this.conversationId,
          model: this.params?.model,
        },
        recording: this.params?.recordingTemplateUrl ? { templateUrl: this.params.recordingTemplateUrl } : undefined,
        room: this.params?.roomName ? { name: this.params.roomName } : undefined,
      },
    };
    this.socket?.send(JSON.stringify(obj));
  }

  private async handleSocketMessage(event: MessageEvent) {
    const msg = JSON.parse(event.data);
    switch (msg.type) {
      case 'room_info':
        this.room = new Room();
        this.room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => this.handleTrackSubscribed(track));
        this.room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant: any) =>
          this.handleDataReceived(payload, participant)
        );
        await this.room.connect(msg.roomUrl, msg.token);
        console.log(`[voiceSession] connected to room ${this.room.name}`);
        this.startPinger();
        this.maybePublishLocalAudio();
        break;
      default:
        console.warn('unknown message type', msg.type);
    }
  }

  private handleSocketClose(event: CloseEvent) {
    console.log(`[voiceSession] socket closed: ${event.code} ${event.reason}`);
    this.changeState(VoiceSessionState.DISCONNECTED);
    if (event.code === 1000) {
      // We initiated this shutdown, so we've already cleaned up.
      // Reconnect to prepare for the next session.
      console.log('[voiceSession] socket closed normally');
    } else {
      console.warn(`[voiceSession] socket closed unexpectedly: ${event.code} ${event.reason}`);
      this.onError?.(new VoiceSessionError(`Socket closed unexpectedly: ${event.code} ${event.reason}`));
    }
  }

  private handleTrackSubscribed(track: RemoteTrack) {
    console.log(`[voiceSession] subscribed to remote audio track ${track.sid}`);
    const audioTrack = track as RemoteAudioTrack;
    audioTrack.on(TrackEvent.AudioPlaybackStarted, () => console.log('[voiceSession] audio playback started'));
    audioTrack.on(TrackEvent.AudioPlaybackFailed, (err: any) => {
      console.error('[voiceSession] audio playback failed', err);
    });
    audioTrack.attach(this.audioElement);
    this.outAnalyzer = new StreamAnalyzer(this.audioContext, track.mediaStream!);
    if (this.delayedSpeakingState) {
      this.delayedSpeakingState = false;
      this.changeState(VoiceSessionState.SPEAKING);
    }
  }

  private handleDataReceived(payload: Uint8Array, _participant: any) {
    const msg = JSON.parse(this.textDecoder.decode(payload));
    if (msg.type === 'pong') {
      const elapsed_ms = performance.now() - msg.timestamp;
      this.handleLatency('workerRtt', elapsed_ms);
    } else if (msg.type === 'state') {
      const newState = msg.state;
      if (newState === VoiceSessionState.SPEAKING && this.outAnalyzer === undefined) {
        // Skip the first speaking state, before we've attached the audio element.
        // handleTrackSubscribed will be called soon and will change the state.
        this.delayedSpeakingState = true;
      } else {
        this.changeState(newState);
      }
    } else if (msg.type === 'transcript') {
      this.handleInputChange(
        msg.transcript.text,
        msg.transcript.stream_timestamp > msg.transcript.last_voice_timestamp,
        msg.transcript.final
      );
    } else if (msg.type === 'voice_synced_transcript') {
      this.handleOutputTranscript(msg);
    } else if (msg.type == 'latency') {
      this.handleLatency(msg.kind, msg.value);
    } else if (msg.type == 'conversation_created') {
      this.conversationId = msg.conversationId;
    }
  }

  private handleInputChange(text: string, voiceEnded: boolean, final: boolean) {
    const vadText = voiceEnded ? ' VAD' : '';
    const finalText = final ? ' FINAL' : '';
    console.log(`[voiceSession] input: ${text}${vadText}${finalText}`);
    this.onInputChange?.(text, final);
  }

  private handleOutputTranscript(msg: any) {
    if (msg.text) {
      this.outputTranscript = msg.text;
    } else if (msg.delta) {
      this.outputTranscript += msg.delta;
    }
    this.onOutputChange?.(this.outputTranscript, msg.final);
    if (msg.final) {
      this.outputTranscript = '';
    }
  }

  private handleLatency(metric: string, value: number) {
    console.log(`[voiceSession] latency: ${metric} ${value.toFixed(0)} ms`);
    this.onLatencyChange?.(metric, value);
  }
}
