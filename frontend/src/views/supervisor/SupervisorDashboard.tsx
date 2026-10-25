import React, { useState } from 'react';
import { Radio, History, Ticket, BookOpen, Search } from 'lucide-react';
import { ActiveCallsList } from './ActiveCallsList';
import { CallHistoryView } from './CallHistoryView';
import { TicketBoardView } from './TicketBoardView';
import { TakeoverPanel } from './TakeoverPanel';
import { Modal } from '../../components/Modal';
import { CallSession, SupervisorProfile } from '../../types';
import { api } from '../../api/client';

interface SupervisorDashboardProps {
  supervisor: SupervisorProfile;
}

export const SupervisorDashboard: React.FC<SupervisorDashboardProps> = ({ supervisor }) => {
  const [subTab, setSubTab] = useState<'active' | 'history' | 'tickets' | 'knowledge'>('active');
  const [selectedTakeoverCall, setSelectedTakeoverCall] = useState<CallSession | null>(null);

  // Knowledge search state
  const [kbQuery, setKbQuery] = useState('');
  const [kbResults, setKbResults] = useState<any[]>([]);
  const [kbLoading, setKbLoading] = useState(false);

  const handleSearchKnowledge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kbQuery.trim()) return;
    setKbLoading(true);
    try {
      const res = await api.queryKnowledge(kbQuery);
      setKbResults(res);
    } catch (e) {
      setKbResults([]);
    } finally {
      setKbLoading(false);
    }
  };

  return (
    <div style={{
      width: '100%',
      maxWidth: '1280px',
      margin: '0 auto',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      padding: '1.25rem 1.5rem',
      boxSizing: 'border-box',
      overflow: 'hidden',
    }}>
      {/* Dashboard Top Tabs */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        borderBottom: '1px solid var(--border-subtle)',
        paddingBottom: '0.75rem',
        marginBottom: '1rem',
        flexShrink: 0,
      }}>
        <button
          id="tab-active-calls"
          onClick={() => setSubTab('active')}
          className="btn"
          style={{
            background: subTab === 'active' ? 'var(--bg-card)' : 'transparent',
            color: subTab === 'active' ? '#ffffff' : 'var(--text-secondary)',
            border: subTab === 'active' ? '1px solid var(--border-subtle)' : 'none',
            fontSize: '0.86rem',
            padding: '0.5rem 0.9rem',
            gap: '0.45rem',
          }}
        >
          <Radio size={15} color={subTab === 'active' ? '#10b981' : undefined} />
          Active Calls
        </button>

        <button
          id="tab-call-history"
          onClick={() => setSubTab('history')}
          className="btn"
          style={{
            background: subTab === 'history' ? 'var(--bg-card)' : 'transparent',
            color: subTab === 'history' ? '#ffffff' : 'var(--text-secondary)',
            border: subTab === 'history' ? '1px solid var(--border-subtle)' : 'none',
            fontSize: '0.86rem',
            padding: '0.5rem 0.9rem',
            gap: '0.45rem',
          }}
        >
          <History size={15} />
          Call History & Transcripts
        </button>

        <button
          id="tab-tickets"
          onClick={() => setSubTab('tickets')}
          className="btn"
          style={{
            background: subTab === 'tickets' ? 'var(--bg-card)' : 'transparent',
            color: subTab === 'tickets' ? '#ffffff' : 'var(--text-secondary)',
            border: subTab === 'tickets' ? '1px solid var(--border-subtle)' : 'none',
            fontSize: '0.86rem',
            padding: '0.5rem 0.9rem',
            gap: '0.45rem',
          }}
        >
          <Ticket size={15} />
          Support Tickets
        </button>

        <button
          id="tab-knowledge"
          onClick={() => setSubTab('knowledge')}
          className="btn"
          style={{
            background: subTab === 'knowledge' ? 'var(--bg-card)' : 'transparent',
            color: subTab === 'knowledge' ? '#ffffff' : 'var(--text-secondary)',
            border: subTab === 'knowledge' ? '1px solid var(--border-subtle)' : 'none',
            fontSize: '0.86rem',
            padding: '0.5rem 0.9rem',
            gap: '0.45rem',
          }}
        >
          <BookOpen size={15} />
          Grounded Knowledge
        </button>
      </div>

      {/* Tab Contents - Scrollable internally */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {subTab === 'active' && <ActiveCallsList />}

        {subTab === 'history' && <CallHistoryView />}

        {subTab === 'tickets' && <TicketBoardView />}

        {subTab === 'knowledge' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div>
              <h2 style={{ fontSize: '1.25rem', color: '#ffffff' }}>Grounded Knowledge Inspection</h2>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                Inspect verified company return and shipping policies available to the voice agent.
              </p>
            </div>

            <form onSubmit={handleSearchKnowledge} style={{ display: 'flex', gap: '0.75rem' }}>
              <input
                id="kb-search-input"
                type="text"
                placeholder="e.g. Can a customer return an opened software or damaged product?"
                value={kbQuery}
                onChange={(e) => setKbQuery(e.target.value)}
                style={{
                  flex: 1,
                  padding: '0.65rem 0.9rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-card)',
                  color: '#ffffff',
                  fontSize: '0.88rem',
                  outline: 'none',
                }}
              />
              <button type="submit" className="btn btn-primary" disabled={kbLoading} style={{ padding: '0.65rem 1.1rem' }}>
                <Search size={15} />
                {kbLoading ? 'Searching...' : 'Search Policy'}
              </button>
            </form>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              {kbResults.length > 0 ? (
                kbResults.map((item, idx) => (
                  <div key={idx} className="card" style={{ padding: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
                        {item.document_title}
                      </span>
                      <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                        Score: {item.score.toFixed(1)}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.85rem', color: '#f8fafc', lineHeight: 1.45 }}>
                      {item.content}
                    </p>
                  </div>
                ))
              ) : (
                <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                    Type a policy query above to verify grounded knowledge retrieved by Epoxa AI.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Takeover Modal */}
      <Modal
        isOpen={selectedTakeoverCall !== null}
        onClose={() => setSelectedTakeoverCall(null)}
        title="Live Supervisor Call Takeover & Transcripts"
        maxWidth="620px"
      >
        {selectedTakeoverCall && (
          <TakeoverPanel
            session={selectedTakeoverCall}
            onClose={() => setSelectedTakeoverCall(null)}
            onRefresh={() => setSelectedTakeoverCall(null)}
          />
        )}
      </Modal>
    </div>
  );
};
