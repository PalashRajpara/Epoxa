import React, { useState, useEffect, useRef } from 'react';
import { Room, RoomEvent } from 'livekit-client';
import { Mic, MicOff, PhoneOff, RefreshCw, Zap, Headphones } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

export default function JoinCallButton({ roomName, sessionId, onConnectionChange, status, onCallEnded }) {
  const [connState, setConnState] = useState('disconnected'); // 'disconnected' | 'connecting' | 'connected' | 'ended'
  const [isMuted, setIsMuted] = useState(false);
  const roomRef = useRef(null);
  const audioElementsRef = useRef(new Map());
  const intentionalDisconnectRef = useRef(false);

  const isEnded = status === 'completed' || status === 'dropped' || status === 'error' || status === 'timeout' || connState === 'ended';

  // Clean up on unmount
  useEffect(() => {
    return () => {
      intentionalDisconnectRef.current = true;
      disconnectRoom();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const markSessionEnded = async () => {
    try {
      await fetch(`${BACKEND_URL}/api/rooms/end-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, room_name: roomName })
      });
    } catch (err) {
      console.warn('[Dashboard LK] Could not mark session ended on backend:', err);
    }
  };

  const handleJoinClick = async () => {
    if (connState !== 'disconnected') return;
    
    setConnState('connecting');
    if (onConnectionChange) onConnectionChange('connecting');

    try {
      // 1. Fetch access token for the human agent from FastAPI backend
      const response = await fetch(`${BACKEND_URL}/api/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_name: roomName,
          participant_name: "Human Agent",
          role: "agent" // Important: tells backend to prefix identity with agent_
        })
      });

      if (!response.ok) {
        throw new Error('Failed to fetch LiveKit token from backend');
      }

      const data = await response.json();
      const serverUrl = data.server_url || 'wss://your-project.livekit.cloud';
      const token = data.token;

      // 2. Instantiate LiveKit Room
      const room = new Room({
        publishDefaults: {
          audioPreset: 'speech',
          dtx: true
        }
      });
      roomRef.current = room;
      intentionalDisconnectRef.current = false;

      // 3. Register room event handlers
      room.on(RoomEvent.ConnectionStateChanged, async (state) => {
        if (state === 'connected') {
          setConnState('connected');
          if (onConnectionChange) onConnectionChange('connected');
        } else if (state === 'disconnected') {
          if (!intentionalDisconnectRef.current) {
            await markSessionEnded();
            setConnState('ended');
            if (onConnectionChange) onConnectionChange('disconnected');
            if (onCallEnded) onCallEnded(sessionId);
          } else {
            setConnState('disconnected');
            if (onConnectionChange) onConnectionChange('disconnected');
          }
          audioElementsRef.current.forEach((el) => el.remove());
          audioElementsRef.current.clear();
          roomRef.current = null;
        }
      });

      // Handle track subscription
      room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        if (track.kind === 'audio') {
          const el = track.attach();
          document.body.appendChild(el);
          audioElementsRef.current.set(track.sid, el);
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
        if (track.kind === 'audio') {
          const el = audioElementsRef.current.get(track.sid);
          if (el) {
            track.detach(el);
            el.remove();
            audioElementsRef.current.delete(track.sid);
          }
        }
      });

      // 4. Connect to Room
      await room.connect(serverUrl, token);
      
      // 5. Enable mic automatically upon joining
      await room.localParticipant.setMicrophoneEnabled(true);
      setIsMuted(false);

    } catch (err) {
      console.error('[Dashboard LK] Failed to join room:', err);
      alert(`Could not join room: ${err.message}`);
      setConnState('disconnected');
      if (onConnectionChange) onConnectionChange('disconnected');
    }
  };

  const toggleMute = async () => {
    if (!roomRef.current) return;
    try {
      const nextMute = !isMuted;
      await roomRef.current.localParticipant.setMicrophoneEnabled(!nextMute);
      setIsMuted(nextMute);
    } catch (err) {
      console.error('[Dashboard LK] Error toggling mute:', err);
    }
  };

  const disconnectRoom = async () => {
    if (!roomRef.current) return;
    intentionalDisconnectRef.current = true;
    try {
      await roomRef.current.localParticipant.setMicrophoneEnabled(false);
      await roomRef.current.disconnect();
    } catch (err) {
      console.error('[Dashboard LK] Error during disconnect:', err);
    } finally {
      audioElementsRef.current.forEach((el) => el.remove());
      audioElementsRef.current.clear();
      roomRef.current = null;
      setConnState('disconnected');
      if (onConnectionChange) onConnectionChange('disconnected');
    }
  };

  const handBackToAI = async () => {
    if (!roomRef.current) return;
    try {
      const encoder = new TextEncoder();
      const data = encoder.encode(JSON.stringify({ action: "resume" }));
      
      await roomRef.current.localParticipant.publishData(data, { reliable: true });
      
      // Brief pause for AI to process resume signal
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      await disconnectRoom();
    } catch (err) {
      console.error('[Dashboard LK] Error handing back to AI:', err);
      alert(`Could not hand back: ${err.message}`);
    }
  };

  if (isEnded) {
    return (
      <div className="supervisor-btn-group">
        <button className="saas-btn saas-btn-secondary" disabled>
          <PhoneOff size={15} />
          <span>Call Ended</span>
        </button>
      </div>
    );
  }

  if (connState === 'disconnected') {
    return (
      <div className="supervisor-btn-group">
        <button className="saas-btn saas-btn-primary supervisor-join-btn" onClick={handleJoinClick}>
          <Headphones size={16} />
          <span>Join Live Call</span>
        </button>
      </div>
    );
  }

  if (connState === 'connecting') {
    return (
      <div className="supervisor-btn-group">
        <button className="saas-btn saas-btn-secondary" disabled>
          <RefreshCw size={15} className="spin-fast" />
          <span>Connecting Live Stream...</span>
        </button>
      </div>
    );
  }

  // Connected Active Deck
  return (
    <div className="supervisor-live-deck">
      {/* Live Badge */}
      <div className="supervisor-live-badge">
        <span className="live-pulse-dot" />
        <span>Supervisor Live</span>
      </div>

      {/* Mute toggle button */}
      <button 
        className={`saas-btn ${isMuted ? 'saas-btn-danger' : 'saas-btn-secondary'}`}
        onClick={toggleMute}
        title={isMuted ? "Unmute your microphone" : "Mute your microphone"}
      >
        {isMuted ? <MicOff size={15} /> : <Mic size={15} />}
        <span>{isMuted ? 'Unmute' : 'Mute'}</span>
      </button>

      {/* Hand back to AI button */}
      <button className="saas-btn saas-btn-emerald" onClick={handBackToAI} title="Resume AI voice assistant">
        <Zap size={15} />
        <span>Hand Back to AI</span>
      </button>

      {/* Leave Room button */}
      <button className="saas-btn saas-btn-danger-solid" onClick={disconnectRoom} title="Leave room">
        <PhoneOff size={15} />
        <span>Leave Call</span>
      </button>

      <style>{`
        .supervisor-btn-group {
          display: flex;
          align-items: center;
        }

        .supervisor-join-btn {
          font-family: var(--saas-font-display);
          font-weight: 700;
          letter-spacing: -0.01em;
        }

        .supervisor-live-deck {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-wrap: wrap;
          background: rgba(15, 18, 26, 0.85);
          border: 1px solid var(--saas-border-medium);
          padding: 6px 12px;
          border-radius: var(--saas-radius-lg);
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
        }

        .supervisor-live-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: 11.5px;
          font-weight: 700;
          color: #34d399;
          background: rgba(16, 185, 129, 0.12);
          padding: 4px 10px;
          border-radius: var(--saas-radius-full);
          border: 1px solid rgba(16, 185, 129, 0.3);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        .live-pulse-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #10b981;
          box-shadow: 0 0 8px #10b981;
          animation: pulseRecord 1.4s infinite alternate;
        }

        .spin-fast {
          animation: spinFast 0.8s linear infinite;
        }

        @keyframes spinFast {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
