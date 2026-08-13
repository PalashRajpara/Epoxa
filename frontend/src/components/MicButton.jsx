import React from 'react';
import { Mic, MicOff } from 'lucide-react';

/**
 * Microphone toggle button component.
 * Displays appropriate icon and applies animation states.
 */
export default function MicButton({ isMuted, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className={`mic-button ${isMuted ? 'muted' : 'active'}`}
      title={isMuted ? 'Unmute Microphone' : 'Mute Microphone'}
      aria-label={isMuted ? 'Unmute' : 'Mute'}
    >
      <div className="mic-icon-container">
        {isMuted ? (
          <MicOff size={24} className="icon-transition" />
        ) : (
          <Mic size={24} className="icon-transition pulse-icon" />
        )}
      </div>
      <span className="mic-label">
        {isMuted ? 'Microphone Muted' : 'Microphone Live'}
      </span>
    </button>
  );
}
