import React, { useState, useRef, useEffect } from 'react';
import JoinRoom from './components/JoinRoom';
import CallScreen from './components/CallScreen';
import { LiveKitHelper } from './livekit_client';
import { Shield, Activity, AlertTriangle, X } from 'lucide-react';

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
  const [toastError, setToastError] = useState(null);

  // Use a ref to persist our LiveKit helper instance across re-renders
  const livekitHelperRef = useRef(null);

  // 2. Initialize the LiveKit Helper on mount
  useEffect(() => {
    livekitHelperRef.current = new LiveKitHelper();

    // BUG-22 FIX: Disconnect LiveKit on tab close/navigation to prevent ghost participants
    const handleBeforeUnload = () => {
      if (livekitHelperRef.current) {
        livekitHelperRef.current.disconnect();
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      // Disconnect on component unmount
      if (livekitHelperRef.current) {
        livekitHelperRef.current.disconnect();
      }
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  // Dismiss toast after 6 seconds
  useEffect(() => {
    if (toastError) {
      const timer = setTimeout(() => {
        setToastError(null);
      }, 6000);
      return () => clearTimeout(timer);
    }
  }, [toastError]);

  // 3. Connect to room handler
  const handleJoin = async ({ participantName, roomName: inputRoomName }) => {
    // BUG-21 FIX: Guard against double-submit if React state update is async
    if (isLoading) return;
    setIsLoading(true);
    setToastError(null);

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
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to fetch access token from backend.');
      }

      const data = await response.json();
      const serverUrl = data.server_url || process.env.REACT_APP_LIVEKIT_URL || 'wss://your-project.livekit.cloud';

      // Step B: Connect to the LiveKit Room
      await livekitHelperRef.current.connect(serverUrl, data.token, {
        onConnectionStateChange: (state) => setConnectionState(state),
        onAgentSpeaking: (speaking) => setIsAgentSpeaking(speaking),
        // BUG-18 FIX: Auto-return to join screen when room disconnects
        onDisconnected: () => {
          setStep('join');
          setConnectionState('disconnected');
          setIsMuted(false);
          setIsAgentSpeaking(false);
        },
        onError: (err) => {
          setToastError(`Connection error: ${err.message}`);
        },
      });

      // Connection succeeded! Transition to CallScreen
      setStep('call');
      setIsMuted(false);
      setIsAgentSpeaking(false);
    } catch (err) {
      console.error('Connection failed:', err);
      setToastError(
        err.message || 'Unable to connect to Voice AI backend. Please verify your services are running.'
      );
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
    if (livekitHelperRef.current) {
      await livekitHelperRef.current.disconnect();
    }
    setStep('join');
    setConnectionState('disconnected');
    setIsMuted(false);
    setIsAgentSpeaking(false);
  };

  return (
    <div className="saas-client-shell saas-ambient-canvas">
      {/* Sleek Top Brand Header Bar */}
      <header className="client-top-nav">
        <div className="client-brand-lockup">
          <div className="brand-icon-box">
            <Shield size={18} className="brand-svg-shield" />
          </div>
          <div className="brand-title-group">
            <span className="brand-primary-name">Epoxcel</span>
            <span className="brand-tagline">Voice AI Network</span>
          </div>
        </div>

        <div className="client-nav-telemetry">
          <div className="status-live-chip">
            <Activity size={13} className="pulse-emerald" />
            <span>AI Voice Node Online</span>
          </div>
        </div>
      </header>

      {/* Floating Error Toast Notification */}
      {toastError && (
        <div className="saas-toast-banner" role="alert">
          <AlertTriangle size={17} className="toast-icon-warn" />
          <div className="toast-body">
            <span className="toast-title">Connection Notice</span>
            <span className="toast-message">{toastError}</span>
          </div>
          <button
            onClick={() => setToastError(null)}
            className="toast-close-btn"
            aria-label="Dismiss notice"
          >
            <X size={15} />
          </button>
        </div>
      )}

      {/* Main Interactive Stage */}
      <main className="client-main-content">
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
      </main>

      <style>{`
        .saas-client-shell {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: space-between;
          padding: 16px 24px 28px;
          box-sizing: border-box;
          position: relative;
          overflow-x: hidden;
        }

        /* Top Header Nav */
        .client-top-nav {
          width: 100%;
          max-width: 1200px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 0;
          z-index: 20;
        }

        .client-brand-lockup {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .brand-icon-box {
          width: 36px;
          height: 36px;
          border-radius: var(--saas-radius-md);
          background: var(--saas-brand-gradient);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
          box-shadow: 0 4px 14px var(--saas-brand-glow);
        }

        .brand-svg-shield {
          color: #ffffff;
        }

        .brand-title-group {
          display: flex;
          flex-direction: column;
          gap: 1px;
        }

        .brand-primary-name {
          font-family: var(--saas-font-display);
          font-size: 16px;
          font-weight: 700;
          letter-spacing: -0.02em;
          color: #ffffff;
        }

        .brand-tagline {
          font-size: 11px;
          color: var(--saas-text-muted);
          font-weight: 500;
        }

        .client-nav-telemetry {
          display: flex;
          align-items: center;
        }

        .status-live-chip {
          display: flex;
          align-items: center;
          gap: 7px;
          padding: 5px 12px;
          background: rgba(16, 185, 129, 0.08);
          border: 1px solid rgba(16, 185, 129, 0.2);
          border-radius: var(--saas-radius-full);
          font-size: 11.5px;
          font-weight: 600;
          color: #34d399;
          letter-spacing: 0.02em;
        }

        .pulse-emerald {
          color: var(--saas-emerald);
          animation: pulseEmerald 1.8s infinite;
        }

        @keyframes pulseEmerald {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.9); }
        }

        /* Toast Alert */
        .saas-toast-banner {
          position: fixed;
          top: 24px;
          left: 50%;
          transform: translateX(-50%);
          max-width: 440px;
          width: calc(100% - 32px);
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 14px 16px;
          background: rgba(26, 17, 16, 0.92);
          backdrop-filter: blur(16px);
          border: 1px solid rgba(239, 68, 68, 0.35);
          border-radius: var(--saas-radius-md);
          box-shadow: 0 16px 36px rgba(0, 0, 0, 0.6), 0 0 20px rgba(239, 68, 68, 0.2);
          z-index: 100;
          animation: toastSlideDown 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes toastSlideDown {
          from {
            opacity: 0;
            transform: translate(-50%, -15px);
          }
          to {
            opacity: 1;
            transform: translate(-50%, 0);
          }
        }

        .toast-icon-warn {
          color: #f87171;
          flex-shrink: 0;
          margin-top: 2px;
        }

        .toast-body {
          display: flex;
          flex-direction: column;
          gap: 2px;
          flex: 1;
        }

        .toast-title {
          font-size: 13px;
          font-weight: 700;
          color: #fecaca;
        }

        .toast-message {
          font-size: 12px;
          color: #e2e8f0;
          line-height: 1.45;
        }

        .toast-close-btn {
          background: transparent;
          border: none;
          color: #94a3b8;
          cursor: pointer;
          padding: 2px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: color var(--saas-transition-fast);
        }

        .toast-close-btn:hover {
          color: #ffffff;
        }

        /* Main Stage Content */
        .client-main-content {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          flex: 1;
          padding: 20px 0;
        }

        @media (max-width: 480px) {
          .saas-client-shell {
            padding: 12px 14px 20px;
          }
          .client-nav-telemetry {
            display: none;
          }
        }
      `}</style>
    </div>
  );
}
