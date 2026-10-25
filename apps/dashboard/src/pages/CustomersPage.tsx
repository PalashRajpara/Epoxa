import React, { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { CustomerResponse } from '@epoxa/api-client';
import { AlertTriangle, ShieldAlert, UserCheck, UserX, Users } from 'lucide-react';

export const CustomersPage: React.FC = () => {
  const { apiClient } = useAuth();
  const [customers, setCustomers] = useState<CustomerResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [customerToAnonymize, setCustomerToAnonymize] = useState<CustomerResponse | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchCustomers = async () => {
    setLoading(true);
    try {
      const res = await apiClient.listCustomers({ limit: 50 });
      setCustomers(res.items);
    } catch (e) {
      console.error('Failed to load customers:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, []);

  const handleAnonymize = async () => {
    if (!customerToAnonymize) return;
    setActionLoading(true);
    try {
      await apiClient.anonymizeCustomer(customerToAnonymize.id);
      setCustomers((prev) =>
        prev.map((c) =>
          c.id === customerToAnonymize.id
            ? {
                ...c,
                name: 'Anonymized Customer',
                email: null,
                phone_e164: '+00000000000',
                anonymized_at: new Date().toISOString(),
              }
            : c
        )
      );
      setCustomerToAnonymize(null);
    } catch (e: any) {
      alert(`Could not anonymize customer: ${e.detail || e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="dashboard-content-layout">
      <div className="section-header-row">
        <div>
          <h1 className="section-title">Customer Registry & Identity</h1>
          <p className="section-subtitle">
            Customers verified by E.164 phone numbers with privacy anonymization compliance.
          </p>
        </div>
      </div>

      <div className="table-card saas-card-glass">
        {loading ? (
          <div className="empty-state-card">
            <span className="btn-spinner" />
            <p>Loading customer profiles...</p>
          </div>
        ) : customers.length === 0 ? (
          <div className="empty-state-card">
            <Users size={32} className="empty-icon" />
            <p>No customer records found.</p>
          </div>
        ) : (
          <div className="table-responsive-container">
            <table className="saas-data-table">
              <thead>
                <tr>
                  <th>Customer Name</th>
                  <th>E.164 Phone</th>
                  <th>Email</th>
                  <th>Tier</th>
                  <th>Privacy Status</th>
                  <th>Registered</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((c) => (
                  <tr key={c.id}>
                    <td className="font-semibold text-primary">{c.name}</td>
                    <td className="saas-mono">{c.phone_e164}</td>
                    <td>{c.email || '—'}</td>
                    <td>
                      <span className={`tier-badge tier-${c.tier.toLowerCase()}`}>{c.tier}</span>
                    </td>
                    <td>
                      {c.anonymized_at ? (
                        <span className="privacy-badge privacy-anonymized">
                          <UserX size={12} /> Anonymized
                        </span>
                      ) : (
                        <span className="privacy-badge privacy-active">
                          <UserCheck size={12} /> Active
                        </span>
                      )}
                    </td>
                    <td className="table-time-cell">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      {!c.anonymized_at && (
                        <button
                          type="button"
                          className="btn-anonymize-sm"
                          onClick={() => setCustomerToAnonymize(c)}
                        >
                          Anonymize
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

      {/* Confirmation Modal: Anonymize Customer */}
      {customerToAnonymize && (
        <div className="modal-backdrop-overlay" role="dialog" aria-modal="true">
          <div className="modal-card saas-card-glass">
            <div className="modal-header">
              <ShieldAlert size={24} className="modal-icon-danger" />
              <h3 className="modal-title">Confirm Privacy Anonymization</h3>
            </div>
            <p className="modal-message">
              Are you sure you want to permanently anonymize customer <strong>{customerToAnonymize.name}</strong> ({customerToAnonymize.phone_e164})?
              Their personal information will be scrubbed to comply with privacy laws, while historic tickets and appointments will remain intact.
            </p>
            <div className="modal-actions-row">
              <button
                type="button"
                className="modal-btn-cancel"
                onClick={() => setCustomerToAnonymize(null)}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="modal-btn-danger"
                onClick={handleAnonymize}
                disabled={actionLoading}
              >
                {actionLoading ? 'Anonymizing...' : 'Permanently Anonymize'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
