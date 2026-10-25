import React, { useEffect, useState } from 'react';
import { ConnectionStatus } from './ConnectionStatus';
import { MicButton } from './MicButton';
import { PhoneOff, Shield, Sparkles, Volume2 } from 'lucide-react';

interface CallScreenProps {
  participantName: string;
  connectionState: string;
  isAgentSpeaking: boolean;
  isMuted: boolean;
  onToggleMic: () => void;
  onEndCall: () => void;
}

export const CallScreen: React.FC<CallScreenProps> = ({
  participantName,
  connectionState,
  isAgentSpeaking,
  isMuted,
  onToggleMic,
  onEndCall,
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatDuration = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="call-screen-container saas-card-glass">
      {/* Top Session Ribbon */}
      <div className="call-top-ribbon">
        <ConnectionStatus state={connectionState} />
        <div className="call-timer-chip">
          <span className="timer-dot" />
          <span className="timer-digits saas-mono">{formatDuration(elapsedSeconds)}</span>
        </div>
      </div>

      {/* Main Visualizer Stage */}
      <div className="voice-stage-center">
        <div className={`orb-visualizer-container ${isAgentSpeaking ? 'orb-speaking' : 'orb-listening'}`}>
          <div className="orb-ring orb-ring-3" />
          <div className="orb-ring orb-ring-2" />
          <div className="orb-ring orb-ring-1" />
          <div className="orb-core">
            <div className="orb-gradient-mesh" />
            <Sparkles size={36} className="orb-sparkle-center" />
          </div>
        </div>

        <div className="agent-status-label-group">
          <h2 className="agent-name-heading">Voice AI Agent</h2>
          <div className="agent-speaking-indicator">
            {isAgentSpeaking ? (
              <span className="status-text-speaking">
                <Volume2 size={16} className="speaking-wave-icon" />
                Voice AI Agent is speaking...
              </span>
            ) : (
              <span className="status-text-listening">
                <span className="listening-pulse-dot" />
                Listening to you...
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Floating Control Bar */}
      <div className="call-controls-glass-bar">
        <MicButton isMuted={isMuted} onToggle={onToggleMic} />

        <button
          type="button"
          onClick={onEndCall}
          className="end-call-btn"
          id="btn-end-call"
          aria-label="End Call"
          title="End Call"
        >
          <div className="end-icon-wrapper">
            <PhoneOff size={22} />
          </div>
          <span className="end-label">End Call</span>
        </button>
      </div>
    </div>
  );
};
