import React from 'react';
import { Mic, MicOff } from 'lucide-react';

interface MicButtonProps {
  isMuted: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export const MicButton: React.FC<MicButtonProps> = ({ isMuted, onToggle, disabled = false }) => {
  return (
    <button
      type="button"
      className={`mic-control-btn ${isMuted ? 'mic-muted' : 'mic-active'}`}
      onClick={onToggle}
      disabled={disabled}
      aria-label={isMuted ? 'Unmute microphone' : 'Mute microphone'}
      title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
    >
      <div className="mic-icon-wrapper">
        {isMuted ? <MicOff size={24} className="mic-icon" /> : <Mic size={24} className="mic-icon" />}
      </div>
      <span className="mic-status-label">{isMuted ? 'Unmute Mic' : 'Mute Mic'}</span>
    </button>
  );
};
