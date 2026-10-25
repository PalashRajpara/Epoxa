import React from 'react';

/**
 * ConnectionStatus: Precision SaaS telemetry status pill.
 * Renders state indicator with subtle micro-glow and reconnecting badge.
 */
export default function ConnectionStatus({
  connectionState = 'disconnected',
  reconnectAttempt = 0,
  maxReconnectAttempts = 3,
}) {
  const getStatusConfig = () => {
    switch (connectionState) {
      case 'connected':
        return {
          label: 'Live Connected',
          dotColor: '#10b981',
          glow: 'rgba(16, 185, 129, 0.4)',
          textColor: '#e2e8f0',
          bgColor: 'rgba(16, 185, 129, 0.08)',
          borderColor: 'rgba(16, 185, 129, 0.25)',
          isPulsing: false,
        };
      case 'connecting':
        return {
          label: 'Connecting...',
          dotColor: '#fbbf24',
          glow: 'rgba(251, 191, 36, 0.4)',
          textColor: '#cbd5e1',
          bgColor: 'rgba(251, 191, 36, 0.08)',
          borderColor: 'rgba(251, 191, 36, 0.25)',
          isPulsing: true,
        };
      case 'reconnecting':
        return {
          label: 'Reconnecting',
          dotColor: '#f97316',
          glow: 'rgba(249, 115, 22, 0.45)',
          textColor: '#fdba74',
          bgColor: 'rgba(249, 115, 22, 0.1)',
          borderColor: 'rgba(249, 115, 22, 0.3)',
          isPulsing: true,
        };
      default:
        return {
          label: 'Disconnected',
          dotColor: '#64748b',
          glow: 'transparent',
          textColor: '#94a3b8',
          bgColor: 'rgba(255, 255, 255, 0.04)',
          borderColor: 'rgba(255, 255, 255, 0.07)',
          isPulsing: false,
        };
    }
  };

  const config = getStatusConfig();
  const showReconnectCount = connectionState === 'reconnecting' && reconnectAttempt > 0;

  return (
    <div
      className="saas-connection-pill"
      style={{
        backgroundColor: config.bgColor,
        borderColor: config.borderColor,
      }}
    >
      {/* Indicator Dot with Ping Ring */}
      <div className="status-dot-wrapper">
        <div
          className="status-solid-dot"
          style={{
            backgroundColor: config.dotColor,
            boxShadow: `0 0 8px ${config.glow}`,
          }}
        />
        {config.isPulsing && (
          <div
            className="status-ping-ring"
            style={{
              borderColor: config.dotColor,
            }}
          />
        )}
      </div>

      {/* Label */}
      <span className="status-pill-label" style={{ color: config.textColor }}>
        {config.label}
      </span>

      {/* Reconnect Attempts Counter Badge */}
      {showReconnectCount && (
        <span className="reconnect-counter-tag saas-mono">
          {reconnectAttempt}/{maxReconnectAttempts}
        </span>
      )}

      <style>{`
        .saas-connection-pill {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 5px 12px;
          border-radius: var(--saas-radius-full);
          border: 1px solid;
          transition: all var(--saas-transition-normal);
          flex-shrink: 0;
        }

        .status-dot-wrapper {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 8px;
          height: 8px;
        }

        .status-solid-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          transition: all var(--saas-transition-fast);
        }

        .status-ping-ring {
          position: absolute;
          width: 7px;
          height: 7px;
          border-radius: 50%;
          border: 1.5px solid;
          animation: statusPing 1.6s cubic-bezier(0, 0, 0.2, 1) infinite;
        }

        @keyframes statusPing {
          0% {
            transform: scale(1);
            opacity: 0.9;
          }
          75%, 100% {
            transform: scale(2.6);
            opacity: 0;
          }
        }

        .status-pill-label {
          font-size: 12px;
          font-weight: 600;
          letter-spacing: 0.02em;
          white-space: nowrap;
        }

        .reconnect-counter-tag {
          font-size: 10.5px;
          font-weight: 700;
          color: #f97316;
          background: rgba(249, 115, 22, 0.18);
          padding: 1px 6px;
          border-radius: var(--saas-radius-full);
          border: 1px solid rgba(249, 115, 22, 0.35);
        }
      `}</style>
    </div>
  );
}
