import React, { useState } from 'react';
import { PhoneCall, User } from 'lucide-react';

/**
 * JoinRoom component: allows the user to enter their name and a room code
 * before connecting to the LiveKit voice server.
 */
export default function JoinRoom({ onJoin, isLoading }) {
  const [participantName, setParticipantName] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!participantName.trim()) {
      alert('Please enter your name before joining.');
      return;
    }

    // Generate a random 5-digit number for a unique private room
    const randomId = Math.floor(10000 + Math.random() * 90000);
    const generatedRoomName = `support-user-${randomId}`;

    onJoin({
      participantName: participantName.trim(),
      roomName: generatedRoomName
    });
  };

  return (
    <div className="join-container">
      <div className="join-card glass">
        <div className="brand-header">
          <div className="pulse-dot-green"></div>
          <h2>Epoxcel Voice Assistant</h2>
          <p className="text-secondary">Speak directly with Epixa, our Voice AI agent</p>
        </div>

        <form onSubmit={handleSubmit} className="join-form">
          {/* User Name Input */}
          <div className="input-group">
            <label htmlFor="participantName">Your Name</label>
            <div className="input-wrapper">
              <User className="input-icon" size={18} />
              <input
                id="participantName"
                type="text"
                value={participantName}
                onChange={(e) => setParticipantName(e.target.value)}
                placeholder="e.g., Vin Diesel"
                disabled={isLoading}
                required
              />
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className={`join-button ${isLoading ? 'loading' : ''}`}
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="spinner">Connecting...</span>
            ) : (
              <>
                <PhoneCall size={18} style={{ marginRight: '8px' }} />
                Call to Agent
              </>
            )}
          </button>
        </form>

        <div className="join-footer">
          <p>Requires microphone access to speak with the AI.</p>
        </div>
      </div>
    </div>
  );
}
