import React, { useState, useRef, useEffect } from 'react';
import JoinRoom from './components/JoinRoom';
import CallScreen from './components/CallScreen';
import { LiveKitHelper } from './livekit_client';

// Define the API base URL for token generation
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

export default function App() {
  // 1. Setup Local States
  const [step, setStep] = useState('join'); // 'join' or 'call'
  const [isLoading, setIsLoading] = useState(false);
  const [roomName, setRoomName] = useState('');
  const [participantName, setParticipantName] = useState('');
  const [connectionState, setConnectionState] = useState('disconnected');
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  // Use a ref to persist our LiveKit helper instance across re-renders
  const livekitHelperRef = useRef(null);

  // 2. Initialize the LiveKit Helper on mount
  useEffect(() => {
    console.log('App component mounted');
    livekitHelperRef.current = new LiveKitHelper();
    return () => {
      console.log('App component unmounted - cleaning up connection');
      // Disconnect on component unmount
      if (livekitHelperRef.current) {
        livekitHelperRef.current.disconnect();
      }
    };
  }, []);

  // 3. Connect to room handler
  const handleJoin = async ({ participantName, roomName: inputRoomName }) => {
    setIsLoading(true);
    const uniqueRoom = inputRoomName.startsWith('support-user-')
      ? inputRoomName
      : `${inputRoomName}-${Math.random().toString(36).substring(2, 7)}`;
    setRoomName(uniqueRoom);
    setParticipantName(participantName);

    try {
      // Step A: Request the token from our FastAPI backend
      const response = await fetch(`${BACKEND_URL}/api/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          room_name: uniqueRoom,
          participant_name: participantName,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch access token from backend');
      }

      const data = await response.json();
      console.log('Successfully received access token from FastAPI:', data);

      // Step B: Connect to the LiveKit Room
      // Resolve the LiveKit WS URL. If it's configured in our local .env,
      // it might be wss://<your-project>.livekit.cloud. We can get it from the backend if needed,
      // or we can pass a static config, or read it from our client settings.
      // But wait! LiveKit client needs the server address. The client address can be fetched
      // from settings or hardcoded/configured. In LiveKit Cloud development, the URL starts with wss://.
      // Let's retrieve it from settings. Since React environment variables start with REACT_APP_,
      // we can read it. Let's make the API return the server URL too, or hardcode it, or read from env.
      // Wait, is there a cleaner way? Let's check: can our backend `/api/token` also send the `LIVEKIT_URL`?
      // Yes! Since the backend already knows `LIVEKIT_URL`, having the backend return it in the token
      // payload makes configuration much easier for a beginner because they only have to configure the backend's `.env`!
      // Let's modify the backend routes/token.py or fetch the URL directly, or read from env.
      // Wait, since we wrote the token route to return:
      // return { "token": jwt_string, "identity": unique_identity, "room": request.room_name, "participant_name": request.participant_name }
      // We can also configure a REACT_APP_LIVEKIT_URL in frontend env, or just return it from the token backend.
      // Wait, let's look at the backend routes/token.py: it does NOT return LIVEKIT_URL.
      // But we can check if REACT_APP_LIVEKIT_URL is in frontend process.env or fallback to a standard.
      // Wait! Let's modify backend routes/token.py to return "server_url" or we can configure it in frontend.
      // Let's return it from backend/routes/token.py to make it even easier!
      // Let's modify backend/routes/token.py in a simple sequential edit if we want, or we can just read it from
      // React's process.env.REACT_APP_LIVEKIT_URL.
      // Wait, to be super robust, let's allow it to read from REACT_APP_LIVEKIT_URL, and fallback to the backend's returned URL if we decide to add it.
      // Let's look at the env. In local development:
      // The user will set LIVEKIT_URL in root `.env`. We can load it on the frontend via process.env or similar, or just read from backend.
      // Let's check: the root `.env` has `LIVEKIT_URL`.
      // If we run React, we can read it directly if we set it up, but react-scripts only loads vars starting with `REACT_APP_`.
      // Therefore, the backend returning the LiveKit URL is an *awesome* and extremely robust design decision!
      // Let's check: did we write backend/routes/token.py? Yes. Let's see if we should edit it to return `LIVEKIT_URL` from the backend environment.
      // That way, the frontend automatically receives the correct WebSocket URL directly from the backend, and the user only has to configure the root `.env` once!
      // That is a genius, beginner-friendly design choice. Let's do that.
      // Wait, let's first update `backend/routes/token.py` to return the `LIVEKIT_URL`. Let's see the replacement chunk.
      // Wait, let's write `App.jsx` first, expecting the backend to return `server_url` (or fallback to REACT_APP_LIVEKIT_URL / root setting).
      
      const serverUrl = data.server_url || process.env.REACT_APP_LIVEKIT_URL || 'wss://your-project.livekit.cloud';

      await livekitHelperRef.current.connect(serverUrl, data.token, {
        onConnectionStateChange: (state) => setConnectionState(state),
        onAgentSpeaking: (speaking) => setIsAgentSpeaking(speaking),
        onError: (err) => alert(`Connection error: ${err.message}`),
      });

      // Connection succeeded! Transition to CallScreen
      setStep('call');
      setIsMuted(false);
      setIsAgentSpeaking(false);
    } catch (err) {
      console.error('Connection failed:', err);
      alert(`Could not connect: ${err.message}. Please check that your backend is running and credentials are set in .env.`);
    } finally {
      setIsLoading(false);
    }
  };

  // 4. Toggle microphone
  const handleToggleMic = async () => {
    const nextMuteState = !isMuted;
    setIsMuted(nextMuteState);
    if (livekitHelperRef.current) {
      await livekitHelperRef.current.setMicrophoneEnabled(!nextMuteState);
    }
  };

  // 5. Disconnect call
  const handleDisconnect = async () => {
    console.log('handleDisconnect button handler called');
    console.trace('handleDisconnect trace');
    if (livekitHelperRef.current) {
      await livekitHelperRef.current.disconnect();
    }
    setStep('join');
    setConnectionState('disconnected');
    setIsMuted(false);
    setIsAgentSpeaking(false);
  };

  return (
    <div className="app-wrapper">
      {/* Global CSS Styles injected for full encapsulation */}
      <style>{`
        /* Global CSS reset overrides */
        .app-wrapper {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          width: 100%;
          background: radial-gradient(circle at top right, #1a1e2e, #0d0e12 70%);
          padding: 20px;
          box-sizing: border-box;
        }

        /* Glassmorphism Card Base */
        .glass {
          background: rgba(20, 22, 28, 0.7);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
          border-radius: 24px;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* Join Room Card Layout */
        .join-container, .call-container {
          width: 100%;
          max-width: 440px;
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .join-card, .call-card {
          width: 100%;
          padding: 40px 32px;
          box-sizing: border-box;
          display: flex;
          flex-direction: column;
          gap: 28px;
        }

        /* Brand Styling */
        .brand-header {
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
        }

        .brand-header h2 {
          margin: 0;
          font-size: 26px;
          font-weight: 700;
          background: linear-gradient(135deg, #a78bfa 0%, #6366f1 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          letter-spacing: -0.5px;
        }

        .text-secondary {
          margin: 0;
          font-size: 14px;
          color: #9ca3af;
          font-weight: 400;
        }

        /* Forms & Inputs */
        .join-form {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .input-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .input-group label {
          font-size: 13px;
          font-weight: 500;
          color: #9ca3af;
          margin-left: 4px;
        }

        .input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }

        .input-icon {
          position: absolute;
          left: 14px;
          color: #6b7280;
        }

        .input-wrapper input {
          width: 100%;
          padding: 14px 16px 14px 44px;
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          background: rgba(255, 255, 255, 0.04);
          color: #fff;
          font-size: 15px;
          font-family: inherit;
          outline: none;
          box-sizing: border-box;
          transition: all 0.2s ease;
        }

        .input-wrapper input:focus {
          border-color: #6366f1;
          background: rgba(255, 255, 255, 0.08);
          box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15);
        }

        /* Action Buttons */
        .join-button, .hangup-button, .mic-button {
          font-family: inherit;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          outline: none;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .join-button {
          width: 100%;
          padding: 16px;
          border-radius: 12px;
          border: none;
          background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
          color: white;
          font-size: 16px;
          box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
        }

        .join-button:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
          background: linear-gradient(135deg, #6d70f2 0%, #5a52e6 100%);
        }

        .join-button:active:not(:disabled) {
          transform: translateY(0);
        }

        .join-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        /* Call Screen Header */
        .call-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          width: 100%;
        }

        .connection-pill {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 14px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 20px;
          border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .status-indicator {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background-color: #6b7280;
        }

        .status-indicator.connected {
          background-color: #10b981;
          box-shadow: 0 0 8px #10b981;
        }

        .status-indicator.connecting, .status-indicator.reconnecting {
          background-color: #fbbf24;
          animation: pulse-indicator 1.5s infinite alternate;
        }

        .connection-text {
          font-size: 12px;
          font-weight: 600;
          color: #e5e7eb;
        }

        .capitalize {
          text-transform: capitalize;
        }

        .call-timer {
          font-size: 15px;
          font-weight: 700;
          color: #9ca3af;
          font-variant-numeric: tabular-nums;
        }

        /* Room Details Grid */
        .room-info {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          padding: 14px;
          background: rgba(255, 255, 255, 0.03);
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.04);
        }

        .room-meta {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .room-meta .label {
          font-size: 11px;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .room-meta .value {
          font-size: 14px;
          font-weight: 600;
          color: #f3f4f6;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        /* Voice Visualizer Orb */
        .visualizer-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 20px;
          padding: 20px 0;
          width: 100%;
        }

        .orb-wrapper {
          position: relative;
          width: 130px;
          height: 130px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .voice-orb {
          position: relative;
          width: 90px;
          height: 90px;
          border-radius: 50%;
          background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 0 30px rgba(129, 140, 248, 0.4);
          z-index: 10;
          transition: all 0.5s ease;
        }

        .orb-icon {
          color: white;
          transition: transform 0.3s ease;
        }

        /* Breathing visual effects */
        .pulse-wave {
          position: absolute;
          width: 90px;
          height: 90px;
          border-radius: 50%;
          background: rgba(129, 140, 248, 0.2);
          z-index: 1;
          opacity: 0;
          transition: all 0.5s ease;
        }

        /* Orb talking mode */
        .orb-wrapper.agent-talking .voice-orb {
          transform: scale(1.05);
          background: linear-gradient(135deg, #a78bfa 0%, #ec4899 100%);
          box-shadow: 0 0 45px rgba(167, 139, 250, 0.6);
        }

        .orb-wrapper.agent-talking .orb-icon {
          transform: scale(1.1) rotate(15deg);
        }

        .orb-wrapper.agent-talking .wave-1 {
          animation: wave-pulse 2.2s infinite ease-out;
        }
        .orb-wrapper.agent-talking .wave-2 {
          animation: wave-pulse 2.2s infinite ease-out 0.7s;
        }
        .orb-wrapper.agent-talking .wave-3 {
          animation: wave-pulse 2.2s infinite ease-out 1.4s;
        }

        /* Orb muted mode */
        .orb-wrapper.muted-state .voice-orb {
          background: linear-gradient(135deg, #4b5563 0%, #374151 100%);
          box-shadow: 0 0 15px rgba(75, 85, 99, 0.2);
        }

        /* Silent / idle breathing animations */
        .orb-wrapper:not(.agent-talking):not(.muted-state) .wave-1 {
          animation: orb-breathe 4s infinite ease-in-out;
        }

        .status-label-container {
          min-height: 24px;
        }

        .status-text {
          margin: 0;
          font-size: 14px;
          color: #9ca3af;
          font-weight: 500;
          text-align: center;
        }

        /* Call Footer Controls */
        .call-controls {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 16px;
          width: 100%;
        }

        /* Microphone Button details */
        .mic-button {
          flex: 1;
          flex-direction: row;
          gap: 10px;
          padding: 14px 20px;
          border-radius: 12px;
          font-size: 14px;
          border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .mic-button.active {
          background: rgba(99, 102, 241, 0.1);
          color: #818cf8;
          border-color: rgba(99, 102, 241, 0.2);
        }

        .mic-button.active:hover {
          background: rgba(99, 102, 241, 0.18);
        }

        .mic-button.muted {
          background: rgba(239, 68, 68, 0.1);
          color: #f87171;
          border-color: rgba(239, 68, 68, 0.2);
        }

        .mic-button.muted:hover {
          background: rgba(239, 68, 68, 0.18);
        }

        .pulse-icon {
          animation: subtle-pulse 2s infinite alternate;
        }

        /* Hangup Action */
        .hangup-button {
          padding: 14px 20px;
          border-radius: 12px;
          border: none;
          background: #ef4444;
          color: white;
          font-size: 14px;
          display: flex;
          align-items: center;
          gap: 8px;
          box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3);
        }

        .hangup-button:hover {
          background: #f87171;
          box-shadow: 0 6px 20px rgba(239, 68, 68, 0.45);
          transform: translateY(-1px);
        }

        .hangup-button:active {
          transform: translateY(0);
        }

        .hangup-button:disabled {
          background: #7f1d1d;
          opacity: 0.5;
          cursor: not-allowed;
          box-shadow: none;
          transform: none;
        }

        .hangup-label {
          display: none; /* Hide text on small layouts, show on larger if needed */
        }

        @media (min-width: 380px) {
          .hangup-label {
            display: inline;
          }
        }

        /* Join Page Footer */
        .join-footer {
          text-align: center;
          font-size: 11px;
          color: #6b7280;
        }

        .join-footer p {
          margin: 0;
        }

        /* Brand green glowing indicator */
        .pulse-dot-green {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background-color: #10b981;
          box-shadow: 0 0 12px #10b981;
          margin-bottom: 4px;
          animation: subtle-pulse 1s infinite alternate;
        }

        /* Keyframes */
        @keyframes wave-pulse {
          0% {
            transform: scale(1);
            opacity: 0.8;
          }
          100% {
            transform: scale(1.8);
            opacity: 0;
          }
        }

        @keyframes orb-breathe {
          0%, 100% {
            transform: scale(1);
            opacity: 0.4;
          }
          50% {
            transform: scale(1.15);
            opacity: 0.1;
          }
        }

        @keyframes subtle-pulse {
          0% {
            transform: scale(0.95);
            opacity: 0.8;
          }
          100% {
            transform: scale(1.05);
            opacity: 1;
          }
        }

        @keyframes pulse-indicator {
          0% {
            transform: scale(0.9);
            opacity: 0.6;
          }
          100% {
            transform: scale(1.1);
            opacity: 1;
          }
        }

        @keyframes spinner-spin {
          to {
            transform: rotate(360deg);
          }
        }

        .spinner::before {
          content: '';
          box-sizing: border-box;
          display: inline-block;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          border: 2px solid #ccc;
          border-top-color: #fff;
          animation: spinner-spin 0.6s linear infinite;
          margin-right: 8px;
          vertical-align: middle;
        }
      `}</style>

      {/* 6. Page Routing Layout */}
      {step === 'join' ? (
        <JoinRoom key="join-screen" onJoin={handleJoin} isLoading={isLoading} />
      ) : (
        <CallScreen
          key="call-screen"
          roomName={roomName}
          participantName={participantName}
          connectionState={connectionState}
          isAgentSpeaking={isAgentSpeaking}
          isMuted={isMuted}
          onToggleMic={handleToggleMic}
          onDisconnect={handleDisconnect}
        />
      )}
    </div>
  );
}
