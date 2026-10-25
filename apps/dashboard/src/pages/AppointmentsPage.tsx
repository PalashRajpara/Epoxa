import React, { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { AppointmentResponse } from '@epoxa/api-client';
import { Calendar, CheckCircle2, Clock, MapPin, XCircle } from 'lucide-react';

export const AppointmentsPage: React.FC = () => {
  const { apiClient } = useAuth();
  const [appointments, setAppointments] = useState<AppointmentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');

  const fetchAppointments = async () => {
    setLoading(true);
    try {
      const res = await apiClient.listAppointments({
        status: statusFilter === 'all' ? undefined : statusFilter,
        limit: 50,
      });
      setAppointments(res.items);
    } catch (e) {
      console.error('Failed to load appointments:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, [statusFilter]);

  return (
    <div className="dashboard-content-layout">
      <div className="section-header-row">
        <div>
          <h1 className="section-title">Customer Appointments</h1>
          <p className="section-subtitle">
            Persisted 30-minute consultation slots booked through Voice AI Agent.
          </p>
        </div>

        <div className="filter-controls-group">
          <select
            className="saas-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Appointments</option>
            <option value="confirmed">Confirmed</option>
            <option value="cancelled">Cancelled</option>
            <option value="completed">Completed</option>
          </select>
        </div>
      </div>

      <div className="table-card saas-card-glass">
        {loading ? (
          <div className="empty-state-card">
            <span className="btn-spinner" />
            <p>Loading booked appointments...</p>
          </div>
        ) : appointments.length === 0 ? (
          <div className="empty-state-card">
            <Calendar size={32} className="empty-icon" />
            <p>No appointments found matching filter.</p>
          </div>
        ) : (
          <div className="table-responsive-container">
            <table className="saas-data-table">
              <thead>
                <tr>
                  <th>Confirmation Code</th>
                  <th>Scheduled Time</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th>Notes</th>
                  <th>Created At</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((a) => (
                  <tr key={a.id}>
                    <td className="saas-mono font-semibold text-brand">
                      {a.confirmation_code}
                    </td>
                    <td>
                      <div className="table-time-cell">
                        <Clock size={13} className="inline mr-1 opacity-70" />
                        {new Date(a.scheduled_at).toLocaleDateString([], {
                          weekday: 'short',
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    </td>
                    <td>{a.duration_minutes} mins</td>
                    <td>
                      <span className={`status-pill status-${a.status}`}>{a.status}</span>
                    </td>
                    <td className="table-desc-cell">{a.notes || 'Voice AI Booking'}</td>
                    <td className="table-time-cell">
                      {new Date(a.created_at).toLocaleDateString()}
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
