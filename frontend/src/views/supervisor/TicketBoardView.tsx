import React, { useState, useEffect } from 'react';
import { Ticket, Filter, CheckCircle2, Clock, AlertCircle } from 'lucide-react';
import { api } from '../../api/client';
import { SupportTicket } from '../../types';
import { PriorityBadge } from '../../components/Badge';

export const TicketBoardView: React.FC = () => {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const res = await api.getTickets(statusFilter || undefined, priorityFilter || undefined);
      setTickets(res.items);
    } catch (e) {
      // handle error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [statusFilter, priorityFilter]);

  const handleUpdateStatus = async (ticketId: string, newStatus: string) => {
    try {
      await api.updateTicket(ticketId, { status: newStatus as any });
      fetchTickets();
    } catch (e) {
      // handle error
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: '1.3rem', color: '#ffffff' }}>Support Tickets Queue</h2>
          <p style={{ fontSize: '0.85rem' }}>Customer issues and follow-ups created automatically by voice AI or supervisors.</p>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              padding: '0.45rem 0.8rem',
              borderRadius: '0.5rem',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-card)',
              color: '#ffffff',
              fontSize: '0.82rem',
              outline: 'none',
            }}
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            style={{
              padding: '0.45rem 0.8rem',
              borderRadius: '0.5rem',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-card)',
              color: '#ffffff',
              fontSize: '0.82rem',
              outline: 'none',
            }}
          >
            <option value="">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
        {tickets.length === 0 ? (
          <div className="card" style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '3rem' }}>
            <Ticket size={36} color="#64748b" style={{ margin: '0 auto 1rem' }} />
            <h3 style={{ fontSize: '1.1rem', color: 'var(--text-secondary)' }}>No Tickets Found</h3>
            <p style={{ fontSize: '0.85rem' }}>Try clearing your filters or creating a test ticket.</p>
          </div>
        ) : (
          tickets.map((t) => (
            <div
              key={t.id}
              className="card"
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.85rem',
                borderLeft: t.priority === 'urgent' ? '4px solid #ef4444' : t.priority === 'high' ? '4px solid #f59e0b' : '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-primary)' }}>
                  {t.ticket_number}
                </span>
                <PriorityBadge priority={t.priority} />
              </div>

              <div>
                <h4 style={{ fontSize: '0.98rem', color: '#ffffff', marginBottom: '0.35rem' }}>
                  {t.title}
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                  {t.description}
                </p>
              </div>

              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingTop: '0.75rem',
                borderTop: '1px solid var(--border-subtle)',
                marginTop: 'auto',
              }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {new Date(t.created_at).toLocaleDateString()}
                </span>

                {/* Status Dropdown */}
                <select
                  value={t.status}
                  onChange={(e) => handleUpdateStatus(t.id, e.target.value)}
                  style={{
                    padding: '0.3rem 0.6rem',
                    borderRadius: '0.4rem',
                    border: '1px solid var(--border-subtle)',
                    background: t.status === 'resolved' ? 'rgba(16, 185, 129, 0.15)' : 'var(--bg-main)',
                    color: t.status === 'resolved' ? '#34d399' : '#ffffff',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    outline: 'none',
                    cursor: 'pointer',
                  }}
                >
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="resolved">Resolved</option>
                </select>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
