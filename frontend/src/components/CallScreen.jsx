import React, { useState, useEffect, useRef } from 'react';
import { PhoneOff, Sparkles, Radio, Volume2, Mic, MicOff, Shield } from 'lucide-react';
import MicButton from './MicButton';
import ConnectionStatus from './ConnectionStatus';

/**
 * CallScreen: Active voice session screen.
 * Features state-reactive ambient aura, responsive multi-tiered voice orb,
 * live audio equalizer visualizer bars, and precision wall-clock telemetry.
 */
export default function CallScreen({
  roomName,
  participantName,
  connectionState,
  isAgentSpeaking,
  isMuted,
  onToggleMic,
  onDisconnect,
  reconnectAttempt = 0,
}) {
  const [seconds, setSeconds] = useState(0);
  const [isClickable, setIsClickable] = useState(false);
  const startTimeRef = useRef(null);

  // Prevent accidental click-through on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsClickable(true);
    }, 600);
    return () => clearTimeout(timer);
  }, []);

  // Wall-clock delta timer (resistant to background tab throttling)
  useEffect(() => {
    if (connectionState !== 'connected') return;

    if (!startTimeRef.current) {
      startTimeRef.current = Date.now();
    }

    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
      setSeconds(elapsed);
    }, 1000);

    return () => clearInterval(timer);
  }, [connectionState]);

  const formatTime = (totalSeconds) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Determine current active mode for ambient atmosphere
  const getOrbState = () => {
    if (connectionState === 'reconnecting') return 'reconnecting';
    if (connectionState !== 'connected') return 'connecting';
    if (isMuted) return 'muted';
    if (isAgentSpeaking) return 'speaking';
    return 'listening';
  };

  const currentOrbState = getOrbState();

  const getStatusDisplay = () => {
    switch (currentOrbState) {
      case 'speaking':
        return {
          label: 'Epixa is Speaking',
          sub: 'Voice synthesis in progress',
          color: '#38bdf8',
          icon: <Volume2 size={15} className="status-badge-icon" />
        };
      case 'listening':
        return {
          label: 'Epixa is Listening',
          sub: 'Speak clearly into your microphone',
          color: '#34d399',
          icon: <Mic size={15} className="status-badge-icon" />
        };
      case 'muted':
        return {
          label: 'Microphone Muted',
          sub: 'AI voice input is currently paused',
          color: '#f87171',
          icon: <MicOff size={15} className="status-badge-icon" />
        };
      case 'reconnecting':
        return {
          label: 'Reconnecting Stream...',
          sub: 'Attempting automatic recovery',
          color: '#fbbf24',
          icon: <Radio size={15} className="status-badge-icon pulse-fast" />
        };
      default:
        return {
          label: 'Establishing Session...',
          sub: 'Securing WebRTC media channels',
          color: '#94a3b8',
          icon: <Sparkles size={15} className="status-badge-icon" />
        };
    }
  };

  const statusInfo = getStatusDisplay();

  return (
    <div className={`active-call-layout state-${currentOrbState}`}>
      {/* State-Reactive Ambient Atmospheric Aura */}
      <div className={`ambient-state-glow glow-${currentOrbState}`} />

      <div className="active-call-card saas-card-glass">
        {/* Top Telemetry Header */}
        <div className="call-top-bar">
          <div className="telemetry-left">
            <ConnectionStatus
              connectionState={connectionState}
              reconnectAttempt={reconnectAttempt}
              maxReconnectAttempts={3}
            />
          </div>

          <div className="telemetry-right">
            <div className="live-duration-pill">
              <span className="live-recording-dot" />
              <span className="duration-digits saas-mono">{formatTime(seconds)}</span>
            </div>
          </div>
        </div>

        {/* Participant & Room Meta Tag Strip */}
        <div className="session-meta-strip">
          <div className="meta-tag">
            <span className="meta-tag-label">Room</span>
            <span className="meta-tag-value saas-mono">{roomName}</span>
          </div>
          <div className="meta-tag-divider" />
          <div className="meta-tag">
            <span className="meta-tag-label">Customer</span>
            <span className="meta-tag-value">{participantName}</span>
          </div>
        </div>

        {/* Central Reactive Voice Orb & Soundwaves */}
        <div className="voice-stage-container">
          <div className={`reactive-orb-stage state-${currentOrbState}`}>
            {/* Outer harmonic ripple rings */}
            <div className="ripple-ring ring-outer" />
            <div className="ripple-ring ring-middle" />
            <div className="ripple-ring ring-inner" />

            {/* Central glowing orb sphere */}
            <div className="core-orb-sphere">
              <div className="orb-inner-gloss" />
              <div className="orb-icon-center">
                <Sparkles size={34} className="core-sparkle-icon" />
              </div>
            </div>
          </div>

          {/* Equalizer Sound Wave Bars (shown when speaking or listening) */}
          <div className="equalizer-waveform-row">
            <div className={`wave-bar bar-1 ${currentOrbState}`} />
            <div className={`wave-bar bar-2 ${currentOrbState}`} />
            <div className={`wave-bar bar-3 ${currentOrbState}`} />
            <div className={`wave-bar bar-4 ${currentOrbState}`} />
            <div className={`wave-bar bar-5 ${currentOrbState}`} />
            <div className={`wave-bar bar-6 ${currentOrbState}`} />
            <div className={`wave-bar bar-7 ${currentOrbState}`} />
          </div>

          {/* Dynamic Status Text Plate */}
          <div className="stage-status-plate">
            <div className="status-headline-badge" style={{ borderColor: `${statusInfo.color}33`, color: statusInfo.color }}>
              {statusInfo.icon}
              <span>{statusInfo.label}</span>
            </div>
            <p className="status-caption">{statusInfo.sub}</p>
          </div>
        </div>

        {/* Bottom Tactile Action Toolbar */}
        <div className="call-actions-dock">
          <MicButton isMuted={isMuted} onToggle={onToggleMic} />

          <button
            onClick={isClickable ? onDisconnect : undefined}
            disabled={!isClickable}
            className={`saas-btn saas-btn-danger-solid hangup-action-btn ${!isClickable ? 'disabled' : ''}`}
            title="End Call Session"
            aria-label="End Call Session"
          >
            <PhoneOff size={18} />
            <span className="hangup-action-label">End Call</span>
          </button>
        </div>

        {/* Security watermark */}
        <div className="call-bottom-badge">
          <Shield size={12} className="shield-icon" />
          <span>Encrypted Audio Channel • Epoxcel LiveKit Support</span>
        </div>
      </div>

      <style>{`
        .active-call-layout {
          position: relative;
          width: 100%;
          max-width: 480px;
          display: flex;
          flex-direction: column;
          align-items: center;
          margin: auto;
          padding: 16px;
          box-sizing: border-box;
          z-index: 10;
        }

        /* Ambient Dynamic Backdrops */
        .ambient-state-glow {
          position: absolute;
          top: 35%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 380px;
          height: 380px;
          border-radius: 50%;
          filter: blur(65px);
          opacity: 0.6;
          transition: background var(--saas-transition-smooth), opacity var(--saas-transition-smooth);
          pointer-events: none;
          z-index: -1;
        }

        .glow-speaking {
          background: radial-gradient(circle, rgba(56, 189, 248, 0.35) 0%, rgba(139, 92, 246, 0.2) 50%, transparent 70%);
        }

        .glow-listening {
          background: radial-gradient(circle, rgba(16, 185, 129, 0.28) 0%, rgba(99, 102, 241, 0.18) 50%, transparent 70%);
        }

        .glow-muted {
          background: radial-gradient(circle, rgba(239, 68, 68, 0.25) 0%, rgba(100, 116, 139, 0.12) 50%, transparent 70%);
        }

        .glow-reconnecting {
          background: radial-gradient(circle, rgba(245, 158, 11, 0.3) 0%, rgba(239, 68, 68, 0.15) 50%, transparent 70%);
        }

        .glow-connecting {
          background: radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, transparent 70%);
        }

        .active-call-card {
          width: 100%;
          padding: 28px 26px;
          box-sizing: border-box;
          display: flex;
          flex-direction: column;
          gap: 22px;
        }

        /* Top Bar */
        .call-top-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
        }

        .live-duration-pill {
          display: flex;
          align-items: center;
          gap: 7px;
          padding: 6px 12px;
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid var(--saas-border-subtle);
          border-radius: var(--saas-radius-full);
        }

        .live-recording-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background-color: var(--saas-emerald);
          box-shadow: 0 0 8px var(--saas-emerald);
          animation: pulseRecord 1.4s infinite alternate ease-in-out;
        }

        @keyframes pulseRecord {
          0% { opacity: 0.4; transform: scale(0.85); }
          100% { opacity: 1; transform: scale(1.15); }
        }

        .duration-digits {
          font-size: 13px;
          font-weight: 600;
          color: #e2e8f0;
          letter-spacing: 0.04em;
        }

        /* Meta Tag Strip */
        .session-meta-strip {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 16px;
          background: rgba(255, 255, 255, 0.025);
          border: 1px solid var(--saas-border-subtle);
          border-radius: var(--saas-radius-md);
          gap: 12px;
        }

        .meta-tag {
          display: flex;
          flex-direction: column;
          gap: 2px;
          overflow: hidden;
        }

        .meta-tag-label {
          font-size: 10.5px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--saas-text-muted);
        }

        .meta-tag-value {
          font-size: 12.5px;
          font-weight: 500;
          color: #cbd5e1;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .meta-tag-divider {
          width: 1px;
          height: 24px;
          background: var(--saas-border-subtle);
        }

        /* Reactive Voice Orb Stage */
        .voice-stage-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 18px;
          padding: 16px 0 10px;
        }

        .reactive-orb-stage {
          position: relative;
          width: 140px;
          height: 140px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .ripple-ring {
          position: absolute;
          border-radius: 50%;
          pointer-events: none;
          transition: all var(--saas-transition-normal);
        }

        .ring-outer {
          width: 136px;
          height: 136px;
          border: 1px solid rgba(99, 102, 241, 0.15);
        }

        .ring-middle {
          width: 114px;
          height: 114px;
          border: 1px solid rgba(99, 102, 241, 0.25);
        }

        .ring-inner {
          width: 94px;
          height: 94px;
          border: 1px solid rgba(99, 102, 241, 0.35);
        }

        /* Speaking State Wave Pulsing */
        .reactive-orb-stage.state-speaking .ring-outer {
          border-color: rgba(56, 189, 248, 0.4);
          animation: ringPulseSpeaking 2.2s infinite ease-out;
        }
        .reactive-orb-stage.state-speaking .ring-middle {
          border-color: rgba(168, 85, 247, 0.5);
          animation: ringPulseSpeaking 2.2s infinite ease-out 0.4s;
        }
        .reactive-orb-stage.state-speaking .ring-inner {
          border-color: rgba(217, 70, 239, 0.6);
          animation: ringPulseSpeaking 2.2s infinite ease-out 0.8s;
        }

        /* Listening State Organic Breath */
        .reactive-orb-stage.state-listening .ring-outer {
          border-color: rgba(16, 185, 129, 0.25);
          animation: ringBreatheListening 3.6s infinite ease-in-out;
        }
        .reactive-orb-stage.state-listening .ring-middle {
          border-color: rgba(99, 102, 241, 0.3);
          animation: ringBreatheListening 3.6s infinite ease-in-out 0.6s;
        }

        /* Muted State */
        .reactive-orb-stage.state-muted .ring-outer,
        .reactive-orb-stage.state-muted .ring-middle,
        .reactive-orb-stage.state-muted .ring-inner {
          border-color: rgba(239, 68, 68, 0.15);
          animation: none;
        }

        /* Core Sphere */
        .core-orb-sphere {
          position: relative;
          width: 78px;
          height: 78px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 5;
          transition: all var(--saas-transition-normal);
          box-shadow: 0 0 35px var(--saas-brand-glow);
        }

        .reactive-orb-stage.state-speaking .core-orb-sphere {
          background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #d946ef 100%);
          box-shadow: 0 0 45px rgba(56, 189, 248, 0.55), inset 0 0 15px rgba(255, 255, 255, 0.4);
          transform: scale(1.06);
        }

        .reactive-orb-stage.state-listening .core-orb-sphere {
          background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #10b981 100%);
          box-shadow: 0 0 35px rgba(99, 102, 241, 0.4);
        }

        .reactive-orb-stage.state-muted .core-orb-sphere {
          background: linear-gradient(135deg, #334155 0%, #1e293b 100%);
          box-shadow: 0 0 15px rgba(0, 0, 0, 0.5);
          border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .orb-inner-gloss {
          position: absolute;
          top: 3px;
          left: 12px;
          width: 32px;
          height: 16px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.45);
          filter: blur(1px);
          transform: rotate(-25deg);
          pointer-events: none;
        }

        .orb-icon-center {
          color: #ffffff;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .core-sparkle-icon {
          filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.4));
          transition: transform var(--saas-transition-normal);
        }

        .reactive-orb-stage.state-speaking .core-sparkle-icon {
          transform: scale(1.1) rotate(10deg);
        }

        /* Equalizer Waveform Row */
        .equalizer-waveform-row {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 5px;
          height: 24px;
        }

        .wave-bar {
          width: 3.5px;
          height: 4px;
          border-radius: var(--saas-radius-full);
          background: #475569;
          transition: all var(--saas-transition-fast);
        }

        .wave-bar.speaking {
          background: linear-gradient(180deg, #38bdf8 0%, #c084fc 100%);
          animation: waveEqualizer 1.2s infinite ease-in-out alternate;
        }

        .wave-bar.speaking.bar-1 { animation-delay: 0.1s; }
        .wave-bar.speaking.bar-2 { animation-delay: 0.3s; }
        .wave-bar.speaking.bar-3 { animation-delay: 0.5s; }
        .wave-bar.speaking.bar-4 { animation-delay: 0.2s; }
        .wave-bar.speaking.bar-5 { animation-delay: 0.4s; }
        .wave-bar.speaking.bar-6 { animation-delay: 0.6s; }
        .wave-bar.speaking.bar-7 { animation-delay: 0.15s; }

        .wave-bar.listening {
          background: #34d399;
          animation: waveListening 2.4s infinite ease-in-out alternate;
        }

        .wave-bar.listening.bar-3, .wave-bar.listening.bar-4, .wave-bar.listening.bar-5 {
          height: 8px;
        }

        @keyframes waveEqualizer {
          0% { height: 4px; }
          100% { height: 22px; }
        }

        @keyframes waveListening {
          0% { height: 4px; }
          100% { height: 10px; }
        }

        @keyframes ringPulseSpeaking {
          0% { transform: scale(0.95); opacity: 0.9; }
          100% { transform: scale(1.4); opacity: 0; }
        }

        @keyframes ringBreatheListening {
          0%, 100% { transform: scale(1); opacity: 0.3; }
          50% { transform: scale(1.1); opacity: 0.7; }
        }

        /* Stage Status Plate */
        .stage-status-plate {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 5px;
          text-align: center;
        }

        .status-headline-badge {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          padding: 4px 12px;
          border-radius: var(--saas-radius-full);
          border: 1px solid;
          background: rgba(255, 255, 255, 0.03);
          font-size: 12.5px;
          font-weight: 600;
          letter-spacing: 0.01em;
        }

        .status-caption {
          font-size: 12px;
          color: var(--saas-text-secondary);
          margin: 0;
        }

        /* Bottom Actions Dock */
        .call-actions-dock {
          display: flex;
          align-items: center;
          gap: 12px;
          width: 100%;
          margin-top: 4px;
        }

        .hangup-action-btn {
          flex: 1;
          padding: 13px 20px;
          border-radius: var(--saas-radius-md);
        }

        .call-bottom-badge {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          font-size: 11px;
          color: var(--saas-text-muted);
          border-top: 1px solid var(--saas-border-subtle);
          padding-top: 14px;
        }

        .shield-icon {
          color: #64748b;
        }

        @media (max-width: 480px) {
          .active-call-card {
            padding: 22px 18px;
            border-radius: var(--saas-radius-lg);
          }
          .hangup-action-label {
            font-size: 13px;
          }
        }
      `}</style>
    </div>
  );
}
