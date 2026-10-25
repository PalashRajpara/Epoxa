import React from 'react';
import { Mic, MicOff, Volume2, UserCheck, PhoneOff, Radio } from 'lucide-react';

interface VoiceVisualizerProps {
  state: 'idle' | 'connecting' | 'listening' | 'agent_speaking' | 'supervisor_takeover' | 'ended';
  isMuted?: boolean;
  volume?: number; // 0.0 to 1.0 (real-time input volume from user's microphone)
}

export const VoiceVisualizer: React.FC<VoiceVisualizerProps> = ({ state, isMuted = false, volume = 0 }) => {
  const isUserSpeaking = state === 'listening' && !isMuted && volume > 0.04;
  const isAiSpeaking = state === 'agent_speaking';

  const getGradient = () => {
    if (isMuted) {
      return 'linear-gradient(135deg, #475569 0%, #1e293b 100%)';
    }
    switch (state) {
      case 'agent_speaking':
        return 'linear-gradient(135deg, #06b6d4 0%, #6366f1 100%)';
      case 'listening':
        return isUserSpeaking
          ? 'linear-gradient(135deg, #10b981 0%, #06b6d4 100%)'
          : 'linear-gradient(135deg, #059669 0%, #0d9488 100%)';
      case 'supervisor_takeover':
        return 'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)';
      case 'connecting':
        return 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)';
      case 'ended':
        return 'linear-gradient(135deg, #475569 0%, #1e293b 100%)';
      default:
        return 'linear-gradient(135deg, #334155 0%, #1e293b 100%)';
    }
  };

  const getGlow = () => {
    if (isMuted) {
      return '0 0 15px rgba(100, 116, 139, 0.2)';
    }
    switch (state) {
      case 'agent_speaking':
        return '0 0 45px rgba(6, 182, 212, 0.5)';
      case 'listening':
        return isUserSpeaking
          ? '0 0 50px rgba(16, 185, 129, 0.6)'
          : '0 0 20px rgba(16, 185, 129, 0.25)';
      case 'supervisor_takeover':
        return '0 0 45px rgba(245, 158, 11, 0.45)';
      default:
        return '0 0 25px rgba(99, 102, 241, 0.2)';
    }
  };

  const getStatusText = () => {
    if (isMuted) {
      return 'Microphone Muted (Live waves stopped)';
    }
    switch (state) {
      case 'connecting':
        return 'Establishing Encrypted Audio Session...';
      case 'listening':
        return isUserSpeaking ? 'User Voice Detected • Transcribing...' : 'Epoxa is listening • Speak naturally';
      case 'agent_speaking':
        return 'Epoxa AI Speaking...';
      case 'supervisor_takeover':
        return 'Live Human Supervisor in Call (AI Muted)';
      case 'ended':
        return 'Call Completed';
      default:
        return 'Ready to connect';
    }
  };

  const getIcon = () => {
    if (isMuted) {
      return <MicOff size={38} color="#f87171" />;
    }
    switch (state) {
      case 'agent_speaking':
        return <Volume2 size={40} color="#ffffff" />;
      case 'listening':
        return <Mic size={40} color="#ffffff" />;
      case 'supervisor_takeover':
        return <UserCheck size={40} color="#ffffff" />;
      case 'ended':
        return <PhoneOff size={40} color="#94a3b8" />;
      default:
        return <Radio size={40} color="#ffffff" />;
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1.5rem 1rem',
    }}>
      {/* Outer Visualizer Orb */}
      <div style={{
        position: 'relative',
        width: '160px',
        height: '160px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        {/* Pulsing Aura Ring: Only pulses when not muted and either AI speaks or User Voice is active */}
        {!isMuted && (isAiSpeaking || isUserSpeaking || state === 'supervisor_takeover') && (
          <div style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            background: getGradient(),
            opacity: 0.25,
            animation: 'pulse-ring 2s infinite cubic-bezier(0.4, 0, 0.6, 1)',
          }} />
        )}

        {/* Core Glowing Orb */}
        <div style={{
          width: '115px',
          height: '115px',
          borderRadius: '50%',
          background: getGradient(),
          boxShadow: getGlow(),
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 2,
          transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
          transform: isUserSpeaking || isAiSpeaking ? 'scale(1.08)' : 'scale(1.0)',
        }}>
          {getIcon()}
        </div>
      </div>

      {/* Reactive Frequency Wave Bars: Waves only move when user voice is active or when AI is speaking */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '5px',
        height: '42px',
        marginTop: '1.25rem',
      }}>
        {[30, 55, 42, 68, 50, 62, 36, 72, 46, 64, 38, 52].map((baseHeight, idx) => {
          let height = '3px';
          let shouldAnimate = false;
          let barColor = '#475569';

          if (isMuted) {
            // Muted: Completely flat, zero wave movement
            height = '3px';
            shouldAnimate = false;
            barColor = '#475569';
          } else if (state === 'listening') {
            if (isUserSpeaking) {
              // Real-time reactive height directly from mic decibel volume
              const dynamicHeight = Math.max(4, Math.round(baseHeight * volume * 1.15));
              height = `${dynamicHeight}px`;
              shouldAnimate = false; // Directly driven by requestAnimationFrame volume
              barColor = '#10b981';
            } else {
              // Silent: Flat line, no wave movement
              height = '3px';
              shouldAnimate = false;
              barColor = 'rgba(255, 255, 255, 0.15)';
            }
          } else if (state === 'agent_speaking') {
            // AI speaking wave animation
            height = `${baseHeight * 0.45}px`;
            shouldAnimate = true;
            barColor = '#6366f1';
          } else if (state === 'supervisor_takeover') {
            height = `${baseHeight * 0.4}px`;
            shouldAnimate = true;
            barColor = '#f59e0b';
          }

          const animDuration = `${0.6 + (idx % 4) * 0.18}s`;

          return (
            <div
              key={idx}
              style={{
                width: '4px',
                height: height,
                borderRadius: '999px',
                backgroundColor: barColor,
                transition: 'height 0.08s ease, background-color 0.2s ease',
                animation: shouldAnimate ? `wave-bar ${animDuration} infinite ease-in-out` : 'none',
                animationDelay: `${idx * 0.07}s`,
              }}
            />
          );
        })}
      </div>

      {/* Status Caption */}
      <div style={{
        marginTop: '0.75rem',
        fontSize: '0.88rem',
        fontWeight: 600,
        color: isMuted
          ? '#f87171'
          : state === 'supervisor_takeover'
          ? '#fbbf24'
          : state === 'listening'
          ? isUserSpeaking
            ? '#34d399'
            : 'var(--text-secondary)'
          : '#a5b4fc',
        letterSpacing: '-0.01em',
        textAlign: 'center',
      }}>
        {getStatusText()}
      </div>
    </div>
  );
};
