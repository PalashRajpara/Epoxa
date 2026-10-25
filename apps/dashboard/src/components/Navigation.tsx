import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import {
  Activity,
  Calendar,
  Headphones,
  LifeBuoy,
  LogOut,
  PhoneCall,
  Shield,
  User,
  Users,
} from 'lucide-react';

export const Navigation: React.FC = () => {
  const { profile, signOut } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut();
    navigate('/login');
  };

  const isAdmin = profile?.role === 'admin' || profile?.role === 'owner';

  return (
    <header className="dashboard-top-navbar saas-card-glass">
      <div className="navbar-left">
        <div className="brand-emblem-box">
          <Shield size={20} className="brand-emblem-icon" />
        </div>
        <div className="brand-title-lockup">
          <div className="brand-name-row">
            <span className="brand-name">{profile?.organization_name || 'Voice AI Agent'}</span>
            <span className="brand-version-badge">Production</span>
          </div>
          <span className="brand-subtitle">Voice AI Supervisor Console</span>
        </div>

        <nav className="navbar-links-group" aria-label="Main Navigation">
          <NavLink
            to="/calls"
            className={({ isActive }) =>
              `nav-tab-link ${isActive ? 'nav-tab-active' : ''}`
            }
          >
            <PhoneCall size={15} />
            <span>Live Calls</span>
          </NavLink>

          <NavLink
            to="/tickets"
            className={({ isActive }) =>
              `nav-tab-link ${isActive ? 'nav-tab-active' : ''}`
            }
          >
            <LifeBuoy size={15} />
            <span>Tickets</span>
          </NavLink>

          <NavLink
            to="/appointments"
            className={({ isActive }) =>
              `nav-tab-link ${isActive ? 'nav-tab-active' : ''}`
            }
          >
            <Calendar size={15} />
            <span>Appointments</span>
          </NavLink>

          <NavLink
            to="/customers"
            className={({ isActive }) =>
              `nav-tab-link ${isActive ? 'nav-tab-active' : ''}`
            }
          >
            <Users size={15} />
            <span>Customers</span>
          </NavLink>

          {isAdmin && (
            <NavLink
              to="/team"
              className={({ isActive }) =>
                `nav-tab-link ${isActive ? 'nav-tab-active' : ''}`
              }
            >
              <Shield size={15} />
              <span>Team & RBAC</span>
            </NavLink>
          )}
        </nav>
      </div>

      <div className="navbar-right">
        <div className="system-telemetry-chip">
          <Activity size={13} className="telemetry-live-icon" />
          <span className="telemetry-label">SSE Gateway Connected</span>
        </div>

        <NavLink to="/profile" className="supervisor-profile-chip" title="View Profile">
          <div className="supervisor-av-circle">
            <User size={13} />
          </div>
          <div className="supervisor-text-lockup">
            <span className="supervisor-name-title">{profile?.full_name || 'Supervisor'}</span>
            <span className="supervisor-role-badge">{profile?.role || 'supervisor'}</span>
          </div>
        </NavLink>

        <button
          type="button"
          onClick={handleLogout}
          className="logout-action-btn"
          title="Sign Out"
          aria-label="Sign Out"
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  );
};
