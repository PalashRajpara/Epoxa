import React, { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { Mail, Shield, UserCheck, UserPlus, Users } from 'lucide-react';

interface MemberItem {
  id: string;
  email: string;
  full_name: string;
  role: 'owner' | 'admin' | 'supervisor';
  is_active: boolean;
  created_at: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const TeamPage: React.FC = () => {
  const { profile, token } = useAuth();
  const [members, setMembers] = useState<MemberItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteName, setInviteName] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'supervisor'>('supervisor');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchMembers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/admin/members`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setMembers(data.items || []);
      }
    } catch (e) {
      console.error('Failed to fetch team members:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMembers();
  }, [token]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/admin/members`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          email: inviteEmail,
          full_name: inviteName,
          role: inviteRole,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to invite team member');
      }
      setShowInviteModal(false);
      setInviteEmail('');
      setInviteName('');
      fetchMembers();
    } catch (err: any) {
      alert(`Invite error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="dashboard-content-layout">
      <div className="section-header-row">
        <div>
          <h1 className="section-title">Team & Role-Based Access Control (RBAC)</h1>
          <p className="section-subtitle">
            Manage organization supervisors and administrators with least-privilege scoping.
          </p>
        </div>

        <button
          type="button"
          className="btn-primary-action"
          onClick={() => setShowInviteModal(true)}
        >
          <UserPlus size={16} />
          <span>Invite Member</span>
        </button>
      </div>

      <div className="table-card saas-card-glass">
        {loading ? (
          <div className="empty-state-card">
            <span className="btn-spinner" />
            <p>Loading organization team...</p>
          </div>
        ) : (
          <div className="table-responsive-container">
            <table className="saas-data-table">
              <thead>
                <tr>
                  <th>Full Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Joined At</th>
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id}>
                    <td className="font-semibold text-primary">{m.full_name}</td>
                    <td className="saas-mono">{m.email}</td>
                    <td>
                      <span className={`role-badge role-${m.role}`}>{m.role.toUpperCase()}</span>
                    </td>
                    <td>
                      {m.is_active ? (
                        <span className="status-pill status-confirmed">Active</span>
                      ) : (
                        <span className="status-pill status-cancelled">Inactive</span>
                      )}
                    </td>
                    <td className="table-time-cell">
                      {new Date(m.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showInviteModal && (
        <div className="modal-backdrop-overlay" role="dialog" aria-modal="true">
          <div className="modal-card saas-card-glass">
            <div className="modal-header">
              <UserPlus size={24} className="modal-icon-brand" />
              <h3 className="modal-title">Invite New Team Member</h3>
            </div>

            <form onSubmit={handleInvite} className="modal-form-body">
              <div className="input-group-saas">
                <label className="input-label-saas">Full Name</label>
                <input
                  type="text"
                  placeholder="e.g. Alex Morgan"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                  className="saas-input"
                  required
                />
              </div>

              <div className="input-group-saas">
                <label className="input-label-saas">Work Email</label>
                <input
                  type="email"
                  placeholder="alex@voiceai.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="saas-input"
                  required
                />
              </div>

              <div className="input-group-saas">
                <label className="input-label-saas">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as any)}
                  className="saas-select"
                >
                  <option value="supervisor">Supervisor (Takeover, Tickets, Appointments)</option>
                  <option value="admin">Administrator (Team management, Settings)</option>
                </select>
              </div>

              <div className="modal-actions-row">
                <button
                  type="button"
                  className="modal-btn-cancel"
                  onClick={() => setShowInviteModal(false)}
                  disabled={actionLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="modal-btn-confirm"
                  disabled={actionLoading}
                >
                  {actionLoading ? 'Sending Invitation...' : 'Send Invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
