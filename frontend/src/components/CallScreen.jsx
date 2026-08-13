import React, { useState, useEffect } from 'react';
import { PhoneOff, Sparkles } from 'lucide-react';
import MicButton from './MicButton';
// Phase 3: Import the new animated connection status component
import ConnectionStatus from './ConnectionStatus';

/**
 * Active call screen showing connection status, visual feedback from AI agent,
 * active call timer, and mute/hang-up controls.
 */
export default function CallScreen({
  roomName,
  participantName,
  connectionState,
  isAgentSpeaking,
  isMuted,
  onToggleMic,
  onDisconnect,
  // Phase 3: How many reconnect attempts have been made (shown in the status pill)
  reconnectAttempt = 0,
}) {
  const [seconds, setSeconds] = useState(0);
  const [isClickable, setIsClickable] = useState(false);

  // Prevent accidental click-through on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsClickable(true);
    }, 600);
    return () => clearTimeout(timer);
  }, []);

  // 1. Manage call duration timer
  useEffect(() => {
    if (connectionState !== 'connected') return;

    const timer = setInterval(() => {
      setSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [connectionState]);

  // Format seconds into MM:SS format
  const formatTime = (totalSeconds) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Determine helper message representing current session state
  const getStatusText = () => {
    if (connectionState === 'connecting') return 'Establishing secure connection...';
    if (connectionState === 'reconnecting') return 'Connection lost. Reconnecting...';
    if (connectionState === 'connected') {
      if (isAgentSpeaking) return 'Epixa is speaking...';
      if (isMuted) return 'Microphone muted (AI listening paused)';
      return 'Epixa is listening...';
    }
    return 'Disconnected';
  };

  return (
    <div className="call-container">
      <div className="call-card glass">
        {/* Connection status header */}
        <div className="call-header">
          {/*
            Phase 3: Replace the old static pill with the animated ConnectionStatus component.
            It shows a colored dot + label + reconnect counter badge automatically.
          */}
          <ConnectionStatus
            connectionState={connectionState}
            reconnectAttempt={reconnectAttempt}
            maxReconnectAttempts={3}
          />
          <div className="call-timer">{formatTime(seconds)}</div>
        </div>

        {/* Info panel */}
        <div className="room-info">
          <div className="room-meta">
            <span className="label">Room:</span>
            <span className="value">{roomName}</span>
          </div>
          <div className="room-meta">
            <span className="label">User:</span>
            <span className="value">{participantName}</span>
          </div>
        </div>

        {/* Visualizer Orb (Reacts to speaking state) */}
        <div className="visualizer-container">
          <div className={`orb-wrapper ${isAgentSpeaking ? 'agent-talking' : ''} ${isMuted ? 'muted-state' : ''}`}>
            {/* Visual waves pulsing outwards */}
            <div className="pulse-wave wave-1"></div>
            <div className="pulse-wave wave-2"></div>
            <div className="pulse-wave wave-3"></div>
            <div className="voice-orb">
              <Sparkles size={32} className="orb-icon" />
            </div>
          </div>
          
          <div className="status-label-container">
            <p className="status-text">{getStatusText()}</p>
          </div>
        </div>

        {/* Controls footer */}
        <div className="call-controls">
          {/* Toggle local mic */}
          <MicButton isMuted={isMuted} onToggle={onToggleMic} />

          {/* End Call / Hang Up button */}
          <button
            onClick={isClickable ? onDisconnect : undefined}
            disabled={!isClickable}
            className={`hangup-button ${!isClickable ? 'disabled' : ''}`}
            title="End Session"
            aria-label="End Session"
          >
            <PhoneOff size={24} />
            <span className="hangup-label">End Call</span>
          </button>
        </div>
      </div>
    </div>
  );
}
