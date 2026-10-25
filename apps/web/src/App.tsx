import React, { useEffect, useRef, useState } from 'react';
import { StartCall } from './components/StartCall';
import { CallScreen } from './components/CallScreen';
import { LiveKitHelper } from './livekit_client';
import { AlertCircle, CheckCircle2, Headphones, Shield, X } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function App() {
  const [step, setStep] = useState<'join' | 'call' | 'ended'>('join');
  const [isLoading, setIsLoading] = useState(false);
  const [participantName, setParticipantName] = useState('');
  const [connectionState, setConnectionState] = useState('disconnected');
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [toastError, setToastError] = useState<string | null>(null);
  const [callEndedReason, setCallEndedReason] = useState<string | null>(null);

  const livekitHelperRef = useRef<LiveKitHelper | null>(null);

  useEffect(() => {
    livekitHelperRef.current = new LiveKitHelper();

    const handleBeforeUnload = () => {
      if (livekitHelperRef.current) {
        livekitHelperRef.current.disconnect();
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      if (livekitHelperRef.current) {
        livekitHelperRef.current.disconnect();
      }
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  useEffect(() => {
    if (toastError) {
      const timer = setTimeout(() => setToastError(null), 7000);
      return () => clearTimeout(timer);
    }
  }, [toastError]);

  const handleStartCall = async (params: { participantName?: string; phone?: string }) => {
    if (isLoading) return;
    setIsLoading(true);
    setToastError(null);
    setParticipantName(params.participantName || 'Guest');

    try {
      // 1. Call server-authoritative endpoint POST /api/v1/calls
      const res = await fetch(`${API_BASE_URL}/api/v1/calls`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          participant_name: params.participantName,
          phone: params.phone,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.title || 'Failed to initialize voice session.');
      }

      const data = await res.json();
      const serverUrl = data.livekit_url || import.meta.env.VITE_LIVEKIT_URL;

      // 2. Connect to LiveKit via LiveKitHelper
      await livekitHelperRef.current?.connect(serverUrl, data.token, {
        onConnectionStateChange: (state) => setConnectionState(state),
        onAgentSpeaking: (speaking) => setIsAgentSpeaking(speaking),
        onDisconnected: (reason) => {
          setCallEndedReason(reason ? `Call ended: ${reason}` : 'Call ended normally.');
          setStep('ended');
          setConnectionState('disconnected');
          setIsMuted(false);
          setIsAgentSpeaking(false);
        },
        onError: (err) => {
          setToastError(`Voice connection error: ${err.message}`);
        },
      });

      setStep('call');
      setIsMuted(false);
      setIsAgentSpeaking(false);
    } catch (err: any) {
      console.error('Call initialization failed:', err);
      setToastError(err.message || 'Unable to establish real-time voice call. Please check your backend connection.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleMic = async () => {
    if (!livekitHelperRef.current) return;
    const nextState = !isMuted;
    await livekitHelperRef.current.setMicrophoneEnabled(!nextState);
    setIsMuted(nextState);
  };

  const handleEndCall = async () => {
    if (livekitHelperRef.current) {
      await livekitHelperRef.current.disconnect();
    }
    setCallEndedReason('Call completed by user.');
    setStep('ended');
  };

  return (
    <div className="app-shell-root">
      {/* Toast Notification */}
      {toastError && (
        <div className="toast-notification-banner saas-card-glass" role="alert">
          <AlertCircle size={18} className="toast-icon-error" />
          <span className="toast-message-text">{toastError}</span>
          <button
            type="button"
            className="toast-close-btn"
            onClick={() => setToastError(null)}
            aria-label="Dismiss error"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Background Decorative Mesh Elements */}
      <div className="ambient-background-glow glow-top-left" />
      <div className="ambient-background-glow glow-bottom-right" />

      {/* Main Container Stage */}
      <main className="app-main-viewport">
        {step === 'join' && <StartCall onStart={handleStartCall} isLoading={isLoading} />}

        {step === 'call' && (
          <CallScreen
            participantName={participantName}
            connectionState={connectionState}
            isAgentSpeaking={isAgentSpeaking}
            isMuted={isMuted}
            onToggleMic={handleToggleMic}
            onEndCall={handleEndCall}
          />
        )}

        {step === 'ended' && (
          <div className="call-ended-card saas-card-glass">
            <div className="ended-icon-wrapper">
              <CheckCircle2 size={36} className="ended-check-icon" />
            </div>
            <h2 className="ended-title">Call Concluded</h2>
            <p className="ended-message">
              {callEndedReason || 'Thank you for reaching out to Voice AI Agent. Your support session has ended.'}
            </p>
            <button
              type="button"
              className="start-call-action-btn"
              onClick={() => setStep('join')}
            >
              Start Another Call
            </button>
          </div>
        )}
      </main>

      {/* Footer Branding */}
      <footer className="app-footer-bar">
        <div className="footer-content-lockup">
          <Shield size={14} className="footer-shield" />
          <span className="footer-text">Voice AI Agent Platform • Enterprise Grade</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
