import React from 'react';
import { Activity } from 'lucide-react';

interface ConnectionStatusProps {
  state: string; // 'connecting' | 'connected' | 'reconnecting' | 'disconnected'
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ state }) => {
  const getBadgeClass = () => {
    switch (state) {
      case 'connected':
        return 'status-badge-connected';
      case 'connecting':
      case 'reconnecting':
        return 'status-badge-connecting';
      default:
        return 'status-badge-disconnected';
    }
  };

  const getLabel = () => {
    switch (state) {
      case 'connected':
        return 'Encrypted Real-Time Audio Connected';
      case 'connecting':
        return 'Connecting to Voice Gateway...';
      case 'reconnecting':
        return 'Reconnecting Voice Channel...';
      default:
        return 'Disconnected';
    }
  };

  return (
    <div className={`connection-status-chip ${getBadgeClass()}`}>
      <span className="status-ping-dot" />
      <Activity size={14} className="status-activity-icon" />
      <span className="status-chip-text">{getLabel()}</span>
    </div>
  );
};
