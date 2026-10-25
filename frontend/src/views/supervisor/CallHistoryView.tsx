import React, { useState, useEffect } from 'react';
import { History, Clock, FileText, ChevronRight, Sparkles, CheckCircle2 } from 'lucide-react';
import { api } from '../../api/client';
import { CallSession, TranscriptTurn } from '../../types';
import { StatusBadge } from '../../components/Badge';
import { Modal } from '../../components/Modal';

export const CallHistoryView: React.FC = () => {
  const [calls, setCalls] = useState<CallSession[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedCall, setSelectedCall] = useState<CallSession | null>(null);
  const [transcripts, setTranscripts] = useState<TranscriptTurn[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const res = await api.getCallHistory(page, 15);
        setCalls(res.items);
        setTotal(res.total);
      } catch (e) {
        // handle error
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [page]);

  const openCallDetails = async (call: CallSession) => {
    setSelectedCall(call);
    try {
      const res = await api.getTranscripts(call.id);
      setTranscripts(res);
    } catch (e) {
      setTranscripts([]);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <h2 style={{ fontSize: '1.3rem', color: '#ffffff' }}>Call History & Summaries</h2>
        <p style={{ fontSize: '0.85rem' }}>Review AI-generated summaries, sentiment insights, and verified transcripts.</p>
      </div>

      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
          <thead>
            <tr style={{ background: 'var(--bg-surface)', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '0.9rem 1.25rem', fontWeight: 600 }}>Status</th>
              <th style={{ padding: '0.9rem 1.25rem', fontWeight: 600 }}>Date & Time</th>
              <th style={{ padding: '0.9rem 1.25rem', fontWeight: 600 }}>Duration</th>
              <th style={{ padding: '0.9rem 1.25rem', fontWeight: 600 }}>AI Call Summary</th>
              <th style={{ padding: '0.9rem 1.25rem', fontWeight: 600 }}>Follow-up</th>
              <th style={{ padding: '0.9rem 1.25rem', fontWeight: 600 }}></th>
            </tr>
          </thead>
          <tbody>
            {calls.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  No historical calls recorded yet.
                </td>
              </tr>
            ) : (
              calls.map((call) => (
                <tr
                  key={call.id}
                  onClick={() => openCallDetails(call)}
                  style={{
                    borderBottom: '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td style={{ padding: '1rem 1.25rem' }}>
                    <StatusBadge status={call.status} />
                  </td>
                  <td style={{ padding: '1rem 1.25rem', color: 'var(--text-primary)' }}>
                    {new Date(call.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                  <td style={{ padding: '1rem 1.25rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    {call.duration_seconds ? `${call.duration_seconds}s` : '< 1m'}
                  </td>
                  <td style={{ padding: '1rem 1.25rem', maxWidth: '350px' }}>
                    <div style={{
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      color: call.summary ? 'var(--text-primary)' : 'var(--text-muted)',
                    }}>
                      {call.summary?.summary || 'Session ended without dialogue.'}
                    </div>
                  </td>
                  <td style={{ padding: '1rem 1.25rem' }}>
                    {call.summary?.follow_up_required ? (
                      <span style={{ color: '#f59e0b', fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase' }}>
                        Required
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>None</span>
                    )}
                  </td>
                  <td style={{ padding: '1rem 1.25rem', textAlign: 'right' }}>
                    <ChevronRight size={18} color="#64748b" />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Transcript & Summary Modal */}
      <Modal
        isOpen={selectedCall !== null}
        onClose={() => setSelectedCall(null)}
        title="Call Session Details & Transcripts"
        maxWidth="680px"
      >
        {selectedCall && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* AI Summary Highlight */}
            {selectedCall.summary && (
              <div style={{
                padding: '1rem',
                borderRadius: '0.6rem',
                background: 'rgba(99, 102, 241, 0.08)',
                border: '1px solid rgba(99, 102, 241, 0.25)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#818cf8', fontSize: '0.82rem', fontWeight: 700, marginBottom: '0.35rem' }}>
                  <Sparkles size={16} />
                  AI Call Summary
                </div>
                <p style={{ fontSize: '0.88rem', color: '#f8fafc', lineHeight: 1.45 }}>
                  {selectedCall.summary.summary}
                </p>
                <div style={{ display: 'flex', gap: '1rem', marginTop: '0.75rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  <span>Intent: <strong>{selectedCall.summary.primary_intent || 'General'}</strong></span>
                  <span>Sentiment: <strong>{selectedCall.summary.detected_sentiment || 'Neutral'}</strong></span>
                </div>
              </div>
            )}

            {/* Transcripts */}
            <div>
              <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                Full Conversation Transcript
              </h4>
              <div style={{
                maxHeight: '300px',
                overflowY: 'auto',
                background: 'var(--bg-main)',
                borderRadius: '0.5rem',
                padding: '1rem',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
              }}>
                {transcripts.length === 0 ? (
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                    No recorded transcript dialogue in this session.
                  </p>
                ) : (
                  transcripts.map((t, idx) => (
                    <div key={idx} style={{ fontSize: '0.85rem' }}>
                      <span style={{
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        fontSize: '0.7rem',
                        color: t.speaker === 'customer' ? '#a5b4fc' : t.speaker === 'supervisor' ? '#f59e0b' : '#34d399',
                        marginRight: '0.4rem',
                      }}>
                        {t.speaker}:
                      </span>
                      <span style={{ color: t.is_purged ? '#94a3b8' : '#e2e8f0' }}>
                        {t.content}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
