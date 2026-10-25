import {
  ConnectionState,
  RemoteParticipant,
  RemoteTrackPublication,
  Room,
  RoomEvent,
  Track,
} from 'livekit-client';

export interface LiveKitCallbacks {
  onConnectionStateChange?: (state: ConnectionState) => void;
  onAgentSpeaking?: (speaking: boolean) => void;
  onParticipantConnected?: (participant: RemoteParticipant) => void;
  onParticipantDisconnected?: (participant: RemoteParticipant) => void;
  onDisconnected?: (reason?: string) => void;
  onError?: (err: Error) => void;
}

/**
 * Manages the client-side WebRTC room connection lifecycle and remote audio playback.
 */
export class LiveKitHelper {
  private room: Room | null = null;
  private audioElements: Map<string, HTMLAudioElement> = new Map();

  public getRoom(): Room | null {
    return this.room;
  }

  public async connect(url: string, token: string, callbacks: LiveKitCallbacks = {}): Promise<Room> {
    const {
      onConnectionStateChange,
      onAgentSpeaking,
      onParticipantConnected,
      onParticipantDisconnected,
      onDisconnected,
      onError,
    } = callbacks;

    try {
      this.room = new Room({
        adaptiveStream: true,
        dynacast: true,
        publishDefaults: {
          audioPreset: 'speech',
          dtx: true,
          red: true,
        },
        audioCaptureDefaults: {
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      this.room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
        if (onConnectionStateChange) onConnectionStateChange(state);
      });

      // INVARIANT 3: Explicitly append to body to prevent browser GC of audio elements
      this.room.on(
        RoomEvent.TrackSubscribed,
        (track: Track, _publication: RemoteTrackPublication, _participant: RemoteParticipant) => {
          if (track.kind === Track.Kind.Audio) {
            const audioElement = track.attach();
            audioElement.id = `remote-audio-${track.sid}`;
            document.body.appendChild(audioElement);
            this.audioElements.set(track.sid, audioElement);
          }
        }
      );

      this.room.on(
        RoomEvent.TrackUnsubscribed,
        (track: Track, _publication: RemoteTrackPublication, _participant: RemoteParticipant) => {
          if (track.kind === Track.Kind.Audio) {
            const el = this.audioElements.get(track.sid);
            if (el) {
              track.detach(el);
              el.remove();
              this.audioElements.delete(track.sid);
            }
          }
        }
      );

      this.room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
        if (onAgentSpeaking) {
          const isAgentSpeaking = speakers.some((s) => !s.isLocal);
          onAgentSpeaking(isAgentSpeaking);
        }
      });

      this.room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
        if (onParticipantConnected) onParticipantConnected(participant);
      });

      this.room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
        if (onParticipantDisconnected) onParticipantDisconnected(participant);
      });

      this.room.on(RoomEvent.Disconnected, (reason) => {
        if (onDisconnected) onDisconnected(reason ? String(reason) : undefined);
      });

      await this.room.connect(url, token);

      try {
        await this.setMicrophoneEnabled(true);
      } catch (micErr: any) {
        if (micErr?.name === 'NotAllowedError' || micErr?.message?.includes('Permission')) {
          const userFriendlyError = new Error(
            'Microphone access was denied. Please allow microphone permission in your browser to speak with Voice AI Agent.'
          );
          if (onError) onError(userFriendlyError);
          throw userFriendlyError;
        }
        throw micErr;
      }

      return this.room;
    } catch (err: any) {
      if (onError) onError(err);
      throw err;
    }
  }

  public async setMicrophoneEnabled(enabled: boolean): Promise<void> {
    if (!this.room?.localParticipant) return;
    await this.room.localParticipant.setMicrophoneEnabled(enabled);
  }

  public async disconnect(): Promise<void> {
    if (!this.room) return;
    try {
      this.audioElements.forEach((el, sid) => {
        el.remove();
      });
      this.audioElements.clear();
      await this.room.disconnect();
    } catch (e) {
      console.warn('Error during room disconnect:', e);
    } finally {
      this.room = null;
    }
  }
}
