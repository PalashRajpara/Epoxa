/**
 * frontend/src/components/ConnectionStatus.jsx
 * ================================================
 * A reusable component that displays the current LiveKit connection state
 * with a color-coded pill and animated indicators.
 *
 * WHAT IT SHOWS:
 *   🟢 Connected      — call is active and working
 *   🟡 Connecting...  — establishing connection to LiveKit
 *   🟡 Reconnecting   — connection dropped, auto-recovery in progress
 *   🔴 Disconnected   — not connected to any room
 *
 * HOW TO USE IN A PARENT COMPONENT:
 *   import ConnectionStatus from './ConnectionStatus';
 *   <ConnectionStatus
 *     connectionState="connected"
 *     reconnectAttempt={0}
 *     maxReconnectAttempts={3}
 *   />
 *
 * PROPS:
 *   connectionState (string): LiveKit connection state string.
 *     Possible values: "disconnected", "connecting", "connected", "reconnecting"
 *   reconnectAttempt (number): How many reconnect attempts have been made. Default 0.
 *   maxReconnectAttempts (number): Max reconnect attempts before giving up. Default 3.
 */

import React, { useEffect, useState } from 'react';

// Helper: Maps a connection state string to a display color
// We use CSS custom property values (color names/codes)
const STATE_COLORS = {
  connected: '#10b981',       // Green
  connecting: '#fbbf24',      // Amber
  reconnecting: '#f97316',    // Orange (different from connecting so user can tell)
  disconnected: '#6b7280',    // Gray
};

// Helper: Maps a connection state to a human-readable label
const STATE_LABELS = {
  connected: 'Connected',
  connecting: 'Connecting...',
  reconnecting: 'Reconnecting',
  disconnected: 'Disconnected',
};

export default function ConnectionStatus({
  connectionState = 'disconnected',
  reconnectAttempt = 0,
  maxReconnectAttempts = 3,
}) {
  // Whether to show a pulse animation on the status dot.
  // We pulse during connecting and reconnecting states.
  const isAnimating = connectionState === 'connecting' || connectionState === 'reconnecting';

  // Whether to show the reconnect counter badge (only during reconnecting)
  const showReconnectCount = connectionState === 'reconnecting' && reconnectAttempt > 0;

  // Color for the status dot based on current state
  const dotColor = STATE_COLORS[connectionState] || STATE_COLORS.disconnected;

  // Human-readable label for the current state
  const label = STATE_LABELS[connectionState] || 'Unknown';

  return (
    <div style={styles.pill}>
      {/* ── Status Dot ──────────────────────────────────────── */}
      {/* This is the small colored circle that shows the state at a glance */}
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        {/* The solid colored dot */}
        <div
          style={{
            ...styles.dot,
            backgroundColor: dotColor,
            boxShadow: `0 0 8px ${dotColor}99`, // Soft glow in the same color
          }}
        />
        {/* Pulse ring — only shows when connecting/reconnecting */}
        {isAnimating && (
          <div
            style={{
              ...styles.pulseRing,
              borderColor: dotColor,
              // The CSS animation is defined in the <style> block below
              animation: 'connectionPulse 1.2s ease-out infinite',
            }}
          />
        )}
      </div>

      {/* ── State Label ─────────────────────────────────────── */}
      <span
        style={{
          ...styles.label,
          color: connectionState === 'connected' ? '#e5e7eb' : '#9ca3af',
        }}
      >
        {label}
      </span>

      {/* ── Reconnect Counter ───────────────────────────────── */}
      {/* Only shown when reconnecting so the user knows progress */}
      {showReconnectCount && (
        <span style={styles.reconnectBadge}>
          {reconnectAttempt}/{maxReconnectAttempts}
        </span>
      )}

      {/* ── Inline Keyframe CSS ─────────────────────────────── */}
      {/* We inject the animation CSS directly here so this component is self-contained */}
      <style>{`
        @keyframes connectionPulse {
          0% {
            transform: scale(1);
            opacity: 0.8;
          }
          100% {
            transform: scale(2.4);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
}

// =============================================================================
// STYLES
// =============================================================================
// We use inline styles (plain JavaScript objects) to keep this component
// fully self-contained — no external CSS file needed.
// Style properties use camelCase (e.g., "borderRadius" not "border-radius").

const styles = {
  // The outer pill container
  pill: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 14px',
    background: 'rgba(255, 255, 255, 0.05)',
    borderRadius: '20px',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    // Smooth transition when state changes (e.g., disconnected → connecting)
    transition: 'all 0.3s ease',
    // Don't let it grow too big
    flexShrink: 0,
  },

  // The solid colored status dot
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',          // Makes it a circle
    flexShrink: 0,
    transition: 'background-color 0.3s ease, box-shadow 0.3s ease',
  },

  // The animated pulse ring behind the dot (only visible when animating)
  pulseRing: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    border: '2px solid',          // The border color is set dynamically in JSX
    boxSizing: 'border-box',
  },

  // The text label ("Connected", "Connecting...", etc.)
  label: {
    fontSize: '12px',
    fontWeight: '600',
    letterSpacing: '0.2px',
    transition: 'color 0.3s ease',
    whiteSpace: 'nowrap',
  },

  // The "2/3" reconnect counter badge
  reconnectBadge: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#f97316',             // Orange to match the reconnecting state color
    background: 'rgba(249, 115, 22, 0.15)',
    padding: '1px 6px',
    borderRadius: '8px',
    border: '1px solid rgba(249, 115, 22, 0.3)',
  },
};
