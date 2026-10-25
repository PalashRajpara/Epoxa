import React from 'react';
import { useAuth } from '../auth/AuthContext';
import { Building2, Mail, Shield, User } from 'lucide-react';

export const ProfilePage: React.FC = () => {
  const { profile, user } = useAuth();

  return (
    <div className="dashboard-content-layout">
      <div className="section-header-row">
        <div>
          <h1 className="section-title">Supervisor Account Profile</h1>
          <p className="section-subtitle">
            Authenticated profile and organization tenancy details.
          </p>
        </div>
      </div>

      <div className="profile-grid-cards">
        <div className="profile-card saas-card-glass">
          <div className="profile-avatar-large">
            <User size={36} />
          </div>
          <h2 className="profile-name-lg">{profile?.full_name || 'Staff Member'}</h2>
          <span className="profile-email-sub">{profile?.email || user?.email}</span>
          <span className={`role-badge role-${profile?.role || 'supervisor'} mt-3`}>
            {(profile?.role || 'supervisor').toUpperCase()}
          </span>

          <div className="profile-detail-list">
            <div className="profile-detail-item">
              <span className="detail-key">User ID</span>
              <span className="detail-val saas-mono">{profile?.id || user?.id}</span>
            </div>
            <div className="profile-detail-item">
              <span className="detail-key">Organization</span>
              <span className="detail-val">{profile?.organization_name || 'Voice AI Agent'}</span>
            </div>
            <div className="profile-detail-item">
              <span className="detail-key">Tenant UUID</span>
              <span className="detail-val saas-mono">{profile?.organization_id}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
