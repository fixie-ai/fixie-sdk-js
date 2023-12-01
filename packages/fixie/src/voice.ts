import {
  AgentId,
  ConversationId,
} from './types.js';
import {
  createLocalTracks,
  DataPacket_Kind,
  LocalAudioTrack,
  RemoteAudioTrack,
  RemoteTrack,
  Room,
  RoomEvent,
  Track,
  TrackEvent,
} from 'livekit-client';


/**
 * Represents the state of a VoiceSession.
 */
export enum VoiceSessionState {
  IDLE = 'idle',
  LISTENING = 'listening',
  THINKING = 'thinking',
  SPEAKING = 'speaking',
}

export interface VoiceSessionInit {
  asrProvider?: string;
  asrLanguage?: string;
  model?: string;
  ttsProvider?: string;
  ttsModel?: string;
  ttsVoice?: string;
  webrtcUrl?: string;
}


/**
 * Web Audio AnalyserNode for an audio stream.
 */
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

/**
 * Manages a single voice session with a Fixie agent.
 */
export class VoiceSession {
  private agentId: AgentId
  private conversationId?: ConversationId;
  private params?: VoiceSessionInit;
  private audioContext = new AudioContext();
  private audioElement = new Audio();
  private textEncoder = new TextEncoder();
  private textDecoder = new TextDecoder();
  private _state = VoiceSessionState.IDLE;
  private socket?: WebSocket;
  private room?: Room;
  private localAudioTrack?: LocalAudioTrack;
  private inAnalyzer?: StreamAnalyzer;
  private outAnalyzer?: StreamAnalyzer;
  private pinger?: ReturnType<typeof setInterval>;
  onStateChange?: (state: VoiceSessionState) => void;
  onInputChange?: (text: string, final: boolean) => void;
  onOutputChange?: (text: string, final: boolean) => void;
  onLatencyChange?: (metric: string, value: number) => void;
  onError?: () => void;

  constructor(agentId: AgentId, conversationId?: ConversationId, params?: VoiceSessionInit) {
    this.agentId = agentId;
    this.conversationId = conversationId; 
    this.params = params;
    this.audioContext = new AudioContext();
    this.audioElement = new Audio();
    this.warmup();
  }
  get state() {
    return this._state;
  }
  get inputAnalyzer() {
    return this.inAnalyzer?.analyzer;
  }
  get outputAnalyzer() {
    return this.outAnalyzer?.analyzer;
  }
  warmup() {
    const url = this.params?.webrtcUrl || 'wss://wsapi.fixie.ai';
    this.socket = new WebSocket(url);
    this.socket.onopen = () => this.handleSocketOpen();
    this.socket.onmessage = (event) => this.handleSocketMessage(event);
    this.socket.onclose = (event) => this.handleSocketClose(event);
  }
  async start() {
    console.log('[chat] starting');
    this.audioElement.play();
    const localTracks = await createLocalTracks({ audio: true, video: false });
    this.localAudioTrack = localTracks[0] as LocalAudioTrack;
    console.log('[chat] got mic stream');
    this.inAnalyzer = new StreamAnalyzer(this.audioContext, this.localAudioTrack!.mediaStream!);
    this.pinger = setInterval(() => {
      const obj = { type: 'ping', timestamp: performance.now() };
      this.sendData(obj);
    }, 5000);
    this.maybePublishLocalAudio();
    this.changeState(VoiceSessionState.LISTENING);
  }
  async stop() {
    console.log('[chat] stopping');
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
    this.changeState(VoiceSessionState.IDLE);
  }
  interrupt() {
    console.log('[chat] interrupting');
    const obj = { type: 'interrupt' };
    this.sendData(obj);
  }
  private changeState(state: VoiceSessionState) {
    if (state != this._state) {
      console.log(`[chat] ${this._state} -> ${state}`);
      this._state = state;
      this.onStateChange?.(state);
    }
  }
  private maybePublishLocalAudio() {
    if (this.room && this.room.state == 'connected' && this.localAudioTrack) {
      console.log(`[chat] publishing local audio track`);
      const opts = { name: 'audio', simulcast: false, source: Track.Source.Microphone };
      this.room.localParticipant.publishTrack(this.localAudioTrack, opts);
    }
  }
  private sendData(obj: any) {
    this.room?.localParticipant.publishData(this.textEncoder.encode(JSON.stringify(obj)), DataPacket_Kind.RELIABLE);
  }
  private handleSocketOpen() {
    console.log('[chat] socket opened');
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
      },
    };
    this.socket?.send(JSON.stringify(obj));
  }
  private async handleSocketMessage(event: MessageEvent) {
    const msg = JSON.parse(event.data);
    switch (msg.type) {
      case 'room_info':
        this.room = new Room();
        await this.room.connect(msg.roomUrl, msg.token);
        console.log('[chat] connected to room', msg.roomUrl);
        this.maybePublishLocalAudio();
        this.room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => this.handleTrackSubscribed(track));
        this.room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant: any) => this.handleDataReceived(payload, participant));
        break;
      default:
        console.warn('unknown message type', msg.type);
    }
  }
  private handleSocketClose(event: CloseEvent) {
    console.log(`[chat] socket closed, code=${event.code}, reason=${event.reason}`);
  }
  private handleTrackSubscribed(track: RemoteTrack) {
    console.log(`[chat] subscribed to remote audio track ${track.sid}`);
    const audioTrack = track as RemoteAudioTrack;
    audioTrack.on(TrackEvent.AudioPlaybackStarted, () => console.log(`[chat] audio playback started`));
    audioTrack.on(TrackEvent.AudioPlaybackFailed, (err: any) => console.error(`[chat] audio playback failed`, err));
    audioTrack.attach(this.audioElement);
    this.outAnalyzer = new StreamAnalyzer(this.audioContext, track.mediaStream!);
  }
  private handleDataReceived(payload: Uint8Array, participant: any) {
    const data = JSON.parse(this.textDecoder.decode(payload));
    if (data.type === 'pong') {
      const elapsed_ms = performance.now() - data.timestamp;
      console.debug(`[chat] worker RTT: ${elapsed_ms.toFixed(0)} ms`);
    } else if (data.type === 'state') {
      const newState = data.state;
      this.changeState(newState);
    } else if (data.type === 'transcript') {
      const finalText = data.transcript.final ? ' FINAL' : '';
      console.log(`[chat] input: ${data.transcript.text}${finalText}`);
    } else if (data.type === 'output') {
      console.log(`[chat] output: ${data.text}`);
    }
  }
}

export function createVoiceSession(agentId: AgentId, conversationId: ConversationId, init?: VoiceSessionInit): VoiceSession {
  return new VoiceSession(agentId, conversationId, init);
}