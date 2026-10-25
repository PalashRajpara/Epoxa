import React from 'react';
import { CallStatus, HandoffState } from '../types';

interface StatusBadgeProps {
  status: CallStatus | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  let bg = 'rgba(100, 116, 139, 0.15)';
  let color = '#94a3b8';
  let border = 'rgba(100, 116, 139, 0.25)';
  let label = status;

  if (status === 'active') {
    bg = 'rgba(16, 185, 129, 0.15)';
    color = '#34d399';
    border = 'rgba(16, 185, 129, 0.3)';
    label = 'Active Call';
  } else if (status === 'escalated') {
    bg = 'rgba(239, 68, 68, 0.15)';
    color = '#f87171';
    border = 'rgba(239, 68, 68, 0.3)';
    label = 'Escalation Alert';
  } else if (status === 'supervisor_takeover') {
    bg = 'rgba(245, 158, 11, 0.15)';
    color = '#fbbf24';
    border = 'rgba(245, 158, 11, 0.3)';
    label = 'Supervisor In Call';
  } else if (status === 'initiating') {
    bg = 'rgba(99, 102, 241, 0.15)';
    color = '#a5b4fc';
    border = 'rgba(99, 102, 241, 0.3)';
    label = 'Connecting';
  } else if (status === 'completed') {
    bg = 'rgba(71, 85, 105, 0.2)';
    color = '#94a3b8';
    border = 'rgba(71, 85, 105, 0.3)';
    label = 'Ended';
  }

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.35rem',
      padding: '0.2rem 0.6rem',
      borderRadius: '999px',
      fontSize: '0.72rem',
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
      backgroundColor: bg,
      color: color,
      border: `1px solid ${border}`,
    }}>
      <span style={{
        width: '6px',
        height: '6px',
        borderRadius: '50%',
        backgroundColor: color,
      }} />
      {label}
    </span>
  );
};

interface PriorityBadgeProps {
  priority: 'urgent' | 'high' | 'medium' | 'low';
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ priority }) => {
  let bg = 'rgba(100, 116, 139, 0.15)';
  let color = '#94a3b8';

  if (priority === 'urgent') {
    bg = 'rgba(239, 68, 68, 0.2)';
    color = '#f87171';
  } else if (priority === 'high') {
    bg = 'rgba(245, 158, 11, 0.2)';
    color = '#fbbf24';
  } else if (priority === 'medium') {
    bg = 'rgba(99, 102, 241, 0.2)';
    color = '#a5b4fc';
  } else if (priority === 'low') {
    bg = 'rgba(16, 185, 129, 0.2)';
    color = '#34d399';
  }

  return (
    <span style={{
      padding: '0.15rem 0.5rem',
      borderRadius: '6px',
      fontSize: '0.7rem',
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
      backgroundColor: bg,
      color: color,
    }}>
      {priority}
    </span>
  );
};
