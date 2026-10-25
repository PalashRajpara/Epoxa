import React from 'react';
import { Mic, MicOff } from 'lucide-react';

/**
 * MicButton: Tactile glassmorphic microphone control button.
 * Visually differentiates Live Microphone vs Muted state.
 */
export default function MicButton({ isMuted, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className={`saas-mic-btn ${isMuted ? 'state-muted' : 'state-live'}`}
      title={isMuted ? 'Unmute Microphone (Resume Voice Input)' : 'Mute Microphone (Pause Voice Input)'}
      aria-label={isMuted ? 'Unmute Microphone' : 'Mute Microphone'}
    >
      <div className="mic-icon-wrapper">
        {isMuted ? (
          <MicOff size={18} className="mic-state-icon" />
        ) : (
          <Mic size={18} className="mic-state-icon" />
        )}
      </div>
      
      <span className="mic-state-label">
        {isMuted ? 'Unmute' : 'Mute'}
      </span>

      <style>{`
        .saas-mic-btn {
          flex: 1;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          padding: 13px 18px;
          border-radius: var(--saas-radius-md);
          font-family: var(--saas-font-sans);
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          outline: none;
          transition: all var(--saas-transition-fast);
          box-sizing: border-box;
          border: 1px solid transparent;
        }

        .saas-mic-btn.state-live {
          background: rgba(99, 102, 241, 0.08);
          color: #a5b4fc;
          border-color: rgba(99, 102, 241, 0.25);
          box-shadow: 0 2px 10px rgba(99, 102, 241, 0.15);
        }

        .saas-mic-btn.state-live:hover {
          background: rgba(99, 102, 241, 0.16);
          color: #ffffff;
          border-color: rgba(99, 102, 241, 0.45);
          transform: translateY(-1px);
          box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25);
        }

        .saas-mic-btn.state-muted {
          background: rgba(239, 68, 68, 0.1);
          color: #fca5a5;
          border-color: rgba(239, 68, 68, 0.25);
        }

        .saas-mic-btn.state-muted:hover {
          background: rgba(239, 68, 68, 0.18);
          color: #ffffff;
          border-color: rgba(239, 68, 68, 0.4);
          transform: translateY(-1px);
        }

        .saas-mic-btn:active {
          transform: translateY(0) !important;
        }

        .mic-icon-wrapper {
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .mic-state-icon {
          transition: transform var(--saas-transition-fast);
        }

        .saas-mic-btn:hover .mic-state-icon {
          transform: scale(1.08);
        }

        .mic-state-label {
          letter-spacing: 0.01em;
        }
      `}</style>
    </button>
  );
}
