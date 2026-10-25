import React, { useState, useEffect } from 'react';
import { PhoneOff, RotateCcw, Send, UserCheck, ShieldAlert, Sparkles } from 'lucide-react';
import { api } from '../../api/client';
import { CallSession, TranscriptTurn } from '../../types';

interface TakeoverPanelProps {
  session: CallSession;
  onClose: () => void;
  onRefresh: () => void;
}

export const TakeoverPanel: React.FC<TakeoverPanelProps> = ({ session, onClose, onRefresh }) => {
  const [transcripts, setTranscripts] = useState<TranscriptTurn[]>([]);
  const [takeoverNotes, setTakeoverNotes] = useState('');
  const [isTakingOver, setIsTakingOver] = useState(false);
  const [hasTakenOver, setHasTakenOver] = useState(session.status === 'supervisor_takeover');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Poll transcripts
  useEffect(() => {
    const fetchTranscripts = async () => {
      try {
        const res = await api.getTranscripts(session.id);
        setTranscripts(res);
      } catch (e) {
        // ignore poll error
      }
    };
    fetchTranscripts();
    const interval = setInterval(fetchTranscripts, 2000);
    return () => clearInterval(interval);
  }, [session.id]);

  const handleStartTakeover = async () => {
    setIsTakingOver(true);
    setErrorMsg(null);
    try {
      await api.takeoverCall(session.id, takeoverNotes);
      setHasTakenOver(true);
      onRefresh();
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to take over call');
    } finally {
      setIsTakingOver(false);
    }
  };

  const handleHandback = async () => {
    setErrorMsg(null);
    try {
      await api.handbackCall(session.id, takeoverNotes);
      setHasTakenOver(false);
      onRefresh();
      onClose();
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to hand back call to AI');
    }
  };

  const handleEndCall = async () => {
    try {
      await api.endVoiceSession(session.id);
      onRefresh();
      onClose();
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to terminate call');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {errorMsg && (
        <div style={{
          padding: '0.75rem',
          borderRadius: '0.5rem',
          background: 'rgba(239, 68, 68, 0.15)',
          color: '#f87171',
          fontSize: '0.85rem',
        }}>
          {errorMsg}
        </div>
      )}

      {/* Status Alert Banner */}
      <div style={{
        padding: '0.9rem',
        borderRadius: '0.6rem',
        background: hasTakenOver ? 'rgba(245, 158, 11, 0.12)' : 'rgba(99, 102, 241, 0.1)',
        border: `1px solid ${hasTakenOver ? 'rgba(245, 158, 11, 0.3)' : 'rgba(99, 102, 241, 0.25)'}`,
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
      }}>
        {hasTakenOver ? <UserCheck size={20} color="#fbbf24" /> : <ShieldAlert size={20} color="#818cf8" />}
        <div style={{ fontSize: '0.85rem' }}>
          <strong>{hasTakenOver ? 'Takeover Active' : 'Call Monitored'}</strong>:
          <span style={{ color: 'var(--text-secondary)', marginLeft: '0.25rem' }}>
            {hasTakenOver
              ? 'AI voice is suppressed. Customer hears your microphone.'
              : 'Click Takeover to mute AI and speak directly with customer.'}
          </span>
        </div>
      </div>

      {/* Live Transcript Stream */}
      <div style={{
        height: '240px',
        overflowY: 'auto',
        background: 'var(--bg-main)',
        borderRadius: '0.6rem',
        padding: '0.9rem',
        border: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.65rem',
      }}>
        {transcripts.map((turn, i) => (
          <div key={i} style={{ fontSize: '0.82rem' }}>
            <span style={{
              fontWeight: 700,
              textTransform: 'uppercase',
              fontSize: '0.7rem',
              color: turn.speaker === 'customer' ? '#a5b4fc' : turn.speaker === 'supervisor' ? '#f59e0b' : '#34d399',
              marginRight: '0.4rem',
            }}>
              {turn.speaker}:
            </span>
            <span style={{ color: '#e2e8f0' }}>{turn.content}</span>
          </div>
        ))}
      </div>

      {/* Supervisor Action Form */}
      <div>
        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
          Supervisor Notes / Resolution Summary
        </label>
        <textarea
          rows={2}
          value={takeoverNotes}
          onChange={(e) => setTakeoverNotes(e.target.value)}
          placeholder="e.g. Approved replacement shipment for damaged package..."
          style={{
            width: '100%',
            padding: '0.6rem 0.8rem',
            borderRadius: '0.5rem',
            border: '1px solid var(--border-subtle)',
            background: 'var(--bg-main)',
            color: '#ffffff',
            fontSize: '0.85rem',
            outline: 'none',
            resize: 'none',
          }}
        />
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
        {!hasTakenOver ? (
          <button
            onClick={handleStartTakeover}
            disabled={isTakingOver}
            className="btn btn-warning"
            style={{ padding: '0.65rem 1.25rem' }}
          >
            <UserCheck size={16} />
            {isTakingOver ? 'Joining Call...' : 'Mute AI & Take Over Call'}
          </button>
        ) : (
          <button
            onClick={handleHandback}
            className="btn btn-secondary"
            style={{ padding: '0.65rem 1.25rem' }}
          >
            <RotateCcw size={16} />
            Hand Back to AI
          </button>
        )}

        <button
          onClick={handleEndCall}
          className="btn btn-danger"
          style={{ padding: '0.65rem 1.25rem' }}
        >
          <PhoneOff size={16} />
          End Call
        </button>
      </div>
    </div>
  );
};
