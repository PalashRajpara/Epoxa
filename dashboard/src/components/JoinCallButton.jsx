import React, { useState, useEffect, useRef } from 'react';
import { Room, RoomEvent } from 'livekit-client';
import { Phone, Mic, MicOff, PhoneOff, RefreshCw, Zap } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

export default function JoinCallButton({ roomName, sessionId, onConnectionChange, status, onCallEnded }) {
  const [connState, setConnState] = useState('disconnected'); // 'disconnected' | 'connecting' | 'connected' | 'ended'
  const [isMuted, setIsMuted] = useState(false);
  const roomRef = useRef(null);
  const audioElementsRef = useRef(new Map());
  // Track whether disconnect was triggered intentionally by the agent
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

  // Notify backend that the session has ended
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
        console.log(`[Dashboard LK] Connection state: ${state}`);
        if (state === 'connected') {
          setConnState('connected');
          if (onConnectionChange) onConnectionChange('connected');
        } else if (state === 'disconnected') {
          // If the agent didn't intentionally disconnect, the customer ended the call
          if (!intentionalDisconnectRef.current) {
            // Mark session as ended on backend immediately
            await markSessionEnded();
            setConnState('ended');
            if (onConnectionChange) onConnectionChange('disconnected');
            if (onCallEnded) onCallEnded(sessionId);
          } else {
            setConnState('disconnected');
            if (onConnectionChange) onConnectionChange('disconnected');
          }
          // Clean up audio elements
          audioElementsRef.current.forEach((el) => el.remove());
          audioElementsRef.current.clear();
          roomRef.current = null;
        }
      });

      // Handle track subscription to play customer and AI audio in the dashboard browser
      room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        if (track.kind === 'audio') {
          console.log(`[Dashboard LK] Subscribed to audio track from: ${participant.identity}`);
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
      // Clean up DOM audio tags
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
      // Publish the 'resume' action over the data channel to inform the AI worker
      const encoder = new TextEncoder();
      const data = encoder.encode(JSON.stringify({ action: "resume" }));
      
      // Publish data reliably to all participants
      await roomRef.current.localParticipant.publishData(data, { reliable: true });
      console.log('[Dashboard LK] Resume signal sent. Handing back to AI...');
      
      // Brief pause to ensure packet is sent before disconnecting
      await new Promise(resolve => setTimeout(resolve, 200));
      
      // Leave the room
      await disconnectRoom();
    } catch (err) {
      console.error('[Dashboard LK] Error handing back to AI:', err);
      alert(`Could not hand back: ${err.message}`);
    }
  };

  if (isEnded) {
    return (
      <button className="btn btn-secondary disabled" style={{ cursor: 'not-allowed' }} disabled>
        <PhoneOff size={16} />
        <span>Call Ended</span>
      </button>
    );
  }

  if (connState === 'disconnected') {
    return (
      <button className="btn btn-primary" onClick={handleJoinClick}>
        <Phone size={16} />
        <span>Join Live Call</span>
      </button>
    );
  }

  if (connState === 'connecting') {
    return (
      <button className="btn btn-secondary disabled" disabled>
        <RefreshCw size={16} className="spinning" />
        <span>Connecting to Call...</span>
      </button>
    );
  }

  return (
    <div className="connection-controls">
      {/* Mute toggle button */}
      <button 
        className={`btn ${isMuted ? 'btn-danger' : 'btn-secondary'}`}
        onClick={toggleMute}
      >
        {isMuted ? <MicOff size={16} /> : <Mic size={16} />}
        <span>{isMuted ? 'Unmute Mic' : 'Mute Mic'}</span>
      </button>

      {/* Hand back to AI button */}
      <button className="btn btn-accent" onClick={handBackToAI}>
        <Zap size={16} />
        <span>Hand Back to AI</span>
      </button>

      {/* Force disconnect button */}
      <button className="btn btn-danger-filled" onClick={disconnectRoom}>
        <PhoneOff size={16} />
        <span>Disconnect Call</span>
      </button>

      <style>{`
        .connection-controls {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }

        .btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          border-radius: 12px;
          padding: 10px 18px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          border: 1px solid transparent;
        }

        .btn-primary {
          background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
          color: white;
          box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
        }

        .btn-primary:hover {
          transform: translateY(-1px);
          box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
        }

        .btn-primary.disabled, .btn-primary:disabled {
          background: linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%);
          color: rgba(255, 255, 255, 0.35);
          border: 1px dashed rgba(139, 92, 246, 0.3);
          box-shadow: none;
          cursor: not-allowed;
          transform: none !important;
        }

        .btn-secondary {
          background: rgba(255, 255, 255, 0.04);
          color: #e2e8f0;
          border-color: rgba(255, 255, 255, 0.08);
        }

        .btn-secondary:hover {
          background: rgba(255, 255, 255, 0.08);
        }

        .btn-danger {
          background: rgba(239, 68, 68, 0.08);
          color: #f87171;
          border-color: rgba(239, 68, 68, 0.2);
        }

        .btn-danger:hover {
          background: rgba(239, 68, 68, 0.15);
        }

        .btn-danger-filled {
          background: #ef4444;
          color: white;
          box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
        }

        .btn-danger-filled:hover {
          background: #dc2626;
          transform: translateY(-1px);
        }

        .btn-accent {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
        }

        .btn-accent:hover {
          transform: translateY(-1px);
          box-shadow: 0 6px 16px rgba(16, 185, 129, 0.35);
        }

        .disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .spinning {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
