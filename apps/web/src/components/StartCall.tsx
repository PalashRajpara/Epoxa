import React, { useState } from 'react';
import { Phone, Shield, Sparkles, User, Info, Headphones } from 'lucide-react';

interface StartCallProps {
  onStart: (params: { participantName?: string; phone?: string }) => void;
  isLoading: boolean;
}

export const StartCall: React.FC<StartCallProps> = ({ onStart, isLoading }) => {
  const [participantName, setParticipantName] = useState('');
  const [phone, setPhone] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStart({
      participantName: participantName.trim() || undefined,
      phone: phone.trim() || undefined,
    });
  };

  return (
    <div className="join-container saas-card-glass">
      <div className="join-header-center">
        <div className="brand-orb-logo-box">
          <div className="brand-orb-glow" />
          <Headphones size={28} className="brand-orb-icon" />
        </div>
        <h1 className="join-title">Welcome to Voice AI Agent</h1>
        <p className="join-subtitle">
          Speak directly with your <strong>Voice AI Agent</strong> customer support assistant.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="join-form">
        <div className="input-group-saas">
          <label htmlFor="participant-name" className="input-label-saas">
            Your Name (Optional)
          </label>
          <div className="input-field-wrapper">
            <User size={16} className="input-field-icon" />
            <input
              id="participant-name"
              type="text"
              placeholder="e.g. Sarah Jenkins"
              value={participantName}
              onChange={(e) => setParticipantName(e.target.value)}
              className="saas-input"
              disabled={isLoading}
              maxLength={64}
            />
          </div>
        </div>

        <div className="input-group-saas">
          <label htmlFor="customer-phone" className="input-label-saas">
            Phone Number (Optional for Account Verification)
          </label>
          <div className="input-field-wrapper">
            <Phone size={16} className="input-field-icon" />
            <input
              id="customer-phone"
              type="tel"
              placeholder="e.g. 9876543210 or +91 98765 43210"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="saas-input"
              disabled={isLoading}
            />
          </div>
          <span className="input-hint-text">
            Provide your registered phone number to automatically access appointments and tickets.
          </span>
        </div>

        <button
          type="submit"
          className="start-call-action-btn"
          disabled={isLoading}
          id="btn-start-call"
        >
          {isLoading ? (
            <span className="btn-spinner-row">
              <span className="btn-spinner" />
              Establishing Secure Voice Gateway...
            </span>
          ) : (
            <span className="btn-content-row">
              <Sparkles size={18} className="btn-sparkle" />
              Start Live Voice Call
            </span>
          )}
        </button>
      </form>

      <div className="privacy-disclosure-box">
        <div className="privacy-disclosure-header">
          <Shield size={14} className="privacy-icon" />
          <span className="privacy-title">Voice Privacy & Recording Notice</span>
        </div>
        <p className="privacy-body">
          Calls are processed with end-to-end encryption and transcribed in real-time for customer service, quality assurance, and scheduling purposes.
        </p>
      </div>
    </div>
  );
};
