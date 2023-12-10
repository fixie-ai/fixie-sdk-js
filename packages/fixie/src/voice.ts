import { AgentId, ConversationId } from './types.js';
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

/** Initialization parameters for a VoiceSession. */
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
  private readonly audioContext = new AudioContext();
  private readonly audioElement = new Audio();
  private readonly textEncoder = new TextEncoder();
  private readonly textDecoder = new TextDecoder();
  private _state = VoiceSessionState.IDLE;
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

  /** Called when this VoiceSession changes its state. */
  onStateChange?: (state: VoiceSessionState) => void;

  /** Called when the input changes. */
  onInputChange?: (text: string, final: boolean) => void;

  /** Called when the output changes. */
  onOutputChange?: (text: string, final: boolean) => void;

  /** Called when new latency data is available. */
  onLatencyChange?: (metric: string, value: number) => void;

  /** Called when an error occurs. */
  onError?: () => void;

  constructor(
    private readonly agentId: AgentId,
    private readonly conversationId?: ConversationId,
    private readonly params?: VoiceSessionInit
  ) {
    console.log('[voiceSession] creating VoiceSession');
    this.warmup();
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

  /** Warm up the VoiceSession by making network connections. This is called automatically when the VoiceSession object is created. */
  warmup(): void {
    console.log('[voiceSession] warming up');
    this.audioStarted = false;
    this.started = false;
    const url = this.params?.webrtcUrl ?? 'wss://wsapi.fixie.ai';
    this.socket = new WebSocket(url);
    this.socket.onopen = () => this.handleSocketOpen();
    this.socket.onmessage = (event) => this.handleSocketMessage(event);
    this.socket.onclose = (event) => this.handleSocketClose(event);
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
    this.pinger = setInterval(() => {
      const obj = { type: 'ping', timestamp: performance.now() };
      this.sendData(obj);
    }, 5000);
    this.audioStarted = true;
  }

  /** Start this VoiceSession. This will call startAudio if it has not been called yet.*/
  async start() {
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
    this.changeState(VoiceSessionState.IDLE);
    this.audioStarted = false;
    this.started = false;
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

  private changeState(state: VoiceSessionState) {
    if (state != this._state) {
      console.log(`[voiceSession] ${this._state} -> ${state}`);
      this._state = state;
      this.onStateChange?.(state);
    }
  }

  private maybePublishLocalAudio() {
    if (this.started && this.room && this.room.state == 'connected' && this.localAudioTrack) {
      console.log('[voiceSession] publishing local audio track');
      const opts = { name: 'audio', simulcast: false, source: Track.Source.Microphone };
      this.room.localParticipant.publishTrack(this.localAudioTrack, opts);
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
        console.log(`[voiceSession] connected to room ${this.room.name}`);
        this.maybePublishLocalAudio();
        this.room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => this.handleTrackSubscribed(track));
        this.room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant: any) =>
          this.handleDataReceived(payload, participant)
        );
        break;
      default:
        console.warn('unknown message type', msg.type);
    }
  }

  private handleSocketClose(event: CloseEvent) {
    console.log(`[voiceSession] socket closed: ${event.code} ${event.reason}`);
    if (event.code === 1000) {
      // We initiated this shutdown, so we've already cleaned up.
      // Reconnect to prepare for the next session.
      console.log('[voiceSession] socket closed normally - calling warmup again');
      this.warmup();
    } else if (event.code === 1006) {
      // This occurs when running a Next.js app in debug mode and the VoiceSession is
      // initialized twice, the first socket will receive this error that we can ignore.
      console.log('[voiceSession] got event 1006');
    } else {
      console.warn(`[voiceSession] socket closed unexpectedly: ${event.code} ${event.reason}`);
      this.onError?.();
    }
  }

  private handleTrackSubscribed(track: RemoteTrack) {
    console.log(`[voiceSession] subscribed to remote audio track ${track.sid}`);
    const audioTrack = track as RemoteAudioTrack;
    audioTrack.on(TrackEvent.AudioPlaybackStarted, () => console.log('[voiceSession] audio playback started'));
    audioTrack.on(TrackEvent.AudioPlaybackFailed, (err: any) =>
      console.error('[voiceSession] audio playback failed', err)
    );
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
      console.debug(`[voiceSession] worker RTT: ${elapsed_ms.toFixed(0)} ms`);
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
    } else if (msg.type === 'output') {
      this.handleOutputChange(msg.text, msg.final);
    } else if (msg.type == 'latency') {
      this.handleLatency(msg.kind, msg.value);
    }
  }

  private handleInputChange(text: string, voiceEnded: boolean, final: boolean) {
    const vadText = voiceEnded ? ' VAD' : '';
    const finalText = final ? ' FINAL' : '';
    console.log(`[voiceSession] input: ${text}${vadText}${finalText}`);
    this.onInputChange?.(text, final);
  }

  private handleOutputChange(text: string, final: boolean) {
    console.log(`[voiceSession] output: ${text}`);
    this.onOutputChange?.(text, final);
  }

  private handleLatency(metric: string, value: number) {
    console.log(`[voiceSession] latency: ${metric} ${value.toFixed(0)} ms`);
    this.onLatencyChange?.(metric, value);
  }
}
