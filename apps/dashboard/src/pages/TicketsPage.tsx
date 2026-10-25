import React, { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { TicketResponse } from '@epoxa/api-client';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Filter,
  LifeBuoy,
  Search,
  Tag,
} from 'lucide-react';

export const TicketsPage: React.FC = () => {
  const { apiClient } = useAuth();
  const [tickets, setTickets] = useState<TicketResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const res = await apiClient.listTickets({
        status: statusFilter === 'all' ? undefined : statusFilter,
        category: categoryFilter === 'all' ? undefined : categoryFilter,
        limit: 50,
      });
      setTickets(res.items);
    } catch (e) {
      console.error('Failed to load tickets:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [statusFilter, categoryFilter]);

  const handleUpdateStatus = async (ticketId: string, newStatus: string) => {
    try {
      await apiClient.updateTicket(ticketId, { status: newStatus });
      setTickets((prev) =>
        prev.map((t) => (t.id === ticketId ? { ...t, status: newStatus as any } : t))
      );
    } catch (e: any) {
      alert(`Could not update ticket: ${e.detail || e.message}`);
    }
  };

  return (
    <div className="dashboard-content-layout">
      <div className="section-header-row">
        <div>
          <h1 className="section-title">Support Tickets & Grievances</h1>
          <p className="section-subtitle">
            Customer inquiries and voice escalations filed through Voice AI Agent.
          </p>
        </div>

        <div className="filter-controls-group">
          <select
            className="saas-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>

          <select
            className="saas-select"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="all">All Categories</option>
            <option value="Complaint">Complaint</option>
            <option value="Escalation">Escalation</option>
            <option value="Billing">Billing</option>
            <option value="General">General</option>
          </select>
        </div>
      </div>

      <div className="table-card saas-card-glass">
        {loading ? (
          <div className="empty-state-card">
            <span className="btn-spinner" />
            <p>Loading support tickets...</p>
          </div>
        ) : tickets.length === 0 ? (
          <div className="empty-state-card">
            <LifeBuoy size={32} className="empty-icon" />
            <p>No support tickets found matching the selected filters.</p>
          </div>
        ) : (
          <div className="table-responsive-container">
            <table className="saas-data-table">
              <thead>
                <tr>
                  <th>Ticket</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Description</th>
                  <th>Status</th>
                  <th>Filed At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => (
                  <tr key={t.id}>
                    <td className="saas-mono font-semibold">TKT-{t.number.toString().padStart(6, '0')}</td>
                    <td>
                      <span className="category-pill">{t.category}</span>
                    </td>
                    <td>
                      <span className={`priority-pill priority-${t.priority}`}>{t.priority}</span>
                    </td>
                    <td className="table-desc-cell" title={t.description}>
                      {t.description.length > 60 ? `${t.description.substring(0, 60)}...` : t.description}
                    </td>
                    <td>
                      <span className={`status-pill status-${t.status}`}>{t.status}</span>
                    </td>
                    <td className="table-time-cell">
                      {new Date(t.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td>
                      {t.status !== 'resolved' && (
                        <button
                          type="button"
                          className="btn-resolve-sm"
                          onClick={() => handleUpdateStatus(t.id, 'resolved')}
                        >
                          Resolve
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
