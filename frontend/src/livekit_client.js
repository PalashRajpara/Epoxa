import { Room, RoomEvent } from 'livekit-client';

/**
 * Helper class to manage the LiveKit Room connection lifecycle and event subscribers.
 * This abstracts the SDK complexities away from the React components.
 */
export class LiveKitHelper {
  constructor() {
    this.room = null;
    this.audioElements = new Map(); // Keep track of attached HTMLAudioElements to clean up later
  }

  /**
   * Connect to the LiveKit server using a token.
   * @param {string} url - The wss:// URL of the LiveKit server
   * @param {string} token - The signed JWT from the FastAPI backend
   * @param {object} callbacks - Custom callbacks to handle UI updates on events
   */
  async connect(url, token, callbacks = {}) {
    const {
      onConnectionStateChange,
      onAgentSpeaking,
      onParticipantConnected,
      onParticipantDisconnected,
      onError
    } = callbacks;

    try {
      // 1. Create a new Room instance
      this.room = new Room({
        publishDefaults: {
          audioPreset: 'speech', // Optimize audio bandwidth for human speech
          dtx: true              // Discontinuous Transmission (saves bandwidth when silent)
        }
      });

      // 2. Set up event listeners
      
      // Track connection state (connecting, connected, disconnected, etc.)
      this.room.on(RoomEvent.ConnectionStateChanged, (state) => {
        console.log(`LiveKit room connection state: ${state}`);
        if (onConnectionStateChange) onConnectionStateChange(state);
      });

      // Handle track subscriptions. When the voice agent sends audio, we MUST attach it to the DOM to hear it.
      this.room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        if (track.kind === 'audio') {
          console.log(`Subscribed to remote audio track from: ${participant.identity}`);
          // track.attach() creates and starts an HTMLAudioElement automatically.
          const audioElement = track.attach();
          // Explicitly append to body to prevent browser garbage collection of audio context
          document.body.appendChild(audioElement);
          this.audioElements.set(track.sid, audioElement);
        }
      });

      // Handle track unsubscribed (cleanup)
      this.room.on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
        if (track.kind === 'audio') {
          console.log(`Unsubscribed from audio track from: ${participant.identity}`);
          const el = this.audioElements.get(track.sid);
          if (el) {
            track.detach(el);
            el.remove();
            this.audioElements.delete(track.sid);
          }
        }
      });

      // Detect active speakers (useful to show visualizer when the AI is talking)
      this.room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
        if (onAgentSpeaking) {
          // Check if any remote participant is speaking (which would be our AI agent)
          const isAgentSpeaking = speakers.some(s => !s.isLocal);
          onAgentSpeaking(isAgentSpeaking);
        }
      });

      // Notify when other participants (like the agent) join or leave
      this.room.on(RoomEvent.ParticipantConnected, (participant) => {
        console.log(`Participant connected: ${participant.identity}`);
        if (onParticipantConnected) onParticipantConnected(participant);
      });

      this.room.on(RoomEvent.ParticipantDisconnected, (participant) => {
        console.log(`Participant disconnected: ${participant.identity}`);
        if (onParticipantDisconnected) onParticipantDisconnected(participant);
      });

      // 3. Connect to the room
      await this.room.connect(url, token);
      console.log('Successfully connected to LiveKit room!');
      
      // 4. By default, enable the microphone to start speaking
      await this.setMicrophoneEnabled(true);

      return this.room;
    } catch (err) {
      console.error('Failed to connect to LiveKit room:', err);
      if (onError) onError(err);
      throw err;
    }
  }

  /**
   * Mute or unmute the local user's microphone.
   * @param {boolean} enabled 
   */
  async setMicrophoneEnabled(enabled) {
    if (!this.room) return;
    try {
      await this.room.localParticipant.setMicrophoneEnabled(enabled);
      console.log(`Microphone enabled state set to: ${enabled}`);
    } catch (err) {
      console.error('Failed to toggle microphone state:', err);
    }
  }

  /**
   * Disconnect from the room and clean up tracks.
   */
  async disconnect() {
    if (!this.room) return;
    
    try {
      // Unpublish local tracks
      await this.setMicrophoneEnabled(false);
      
      // Disconnect
      await this.room.disconnect();
      
      // Clean up audio elements from the DOM
      this.audioElements.forEach((el) => el.remove());
      this.audioElements.clear();
      
      this.room = null;
      console.log('Disconnected from LiveKit room.');
    } catch (err) {
      console.error('Error during LiveKit disconnect:', err);
    }
  }
}
