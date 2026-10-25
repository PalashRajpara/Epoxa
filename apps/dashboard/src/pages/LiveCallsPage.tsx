import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { CallSessionResponse, TranscriptTurnResponse } from '@epoxa/api-client';
import { Room, RoomEvent, Track } from 'livekit-client';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Headphones,
  Mic,
  MicOff,
  PhoneCall,
  PhoneOff,
  Radio,
  RotateCcw,
  Search,
  Shield,
  Sparkles,
  User,
  Volume2,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const LiveCallsPage: React.FC = () => {
  const { apiClient, token } = useAuth();

  const [calls, setCalls] = useState<CallSessionResponse[]>([]);
  const [selectedCall, setSelectedCall] = useState<CallSessionResponse | null>(null);
  const [transcripts, setTranscripts] = useState<TranscriptTurnResponse[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isLoadingCalls, setIsLoadingCalls] = useState(true);

  // Takeover & Audio state
  const [isTakeoverActive, setIsTakeoverActive] = useState(false);
  const [isSupervisorMuted, setIsSupervisorMuted] = useState(false);
  const [showTakeoverConfirm, setShowTakeoverConfirm] = useState(false);
  const [showEndCallConfirm, setShowEndCallConfirm] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const supervisorRoomRef = useRef<Room | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll transcript to bottom
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts]);

  // Load initial calls and set up SSE stream
  useEffect(() => {
    let eventSource: EventSource | null = null;

    const fetchInitialCalls = async () => {
      try {
        const res = await apiClient.listCalls({ limit: 50 });
        setCalls(res.items);
        if (res.items.length > 0 && !selectedCall) {
          setSelectedCall(res.items[0]);
        }
      } catch (e) {
        console.error('Failed to load calls:', e);
      } finally {
        setIsLoadingCalls(false);
      }
    };

    fetchInitialCalls();

    // SSE Stream
    if (token) {
      try {
        // SSE connection passing token in query param
        eventSource = new EventSource(`${API_BASE_URL}/api/v1/calls/stream?token=${token}`);

        eventSource.addEventListener('calls', (e) => {
          try {
            const data = JSON.parse(e.data);
            if (Array.isArray(data)) {
              setCalls(data);
              // Update selected call reference
              if (selectedCall) {
                const updated = data.find((c: CallSessionResponse) => c.id === selectedCall.id);
                if (updated) setSelectedCall(updated);
              }
            }
          } catch (err) {
            console.warn('Error parsing SSE calls event:', err);
          }
        });

        eventSource.addEventListener('transcript', (e) => {
          try {
            const turn: TranscriptTurnResponse = JSON.parse(e.data);
            if (selectedCall && turn.session_id === selectedCall.id) {
              setTranscripts((prev) => {
                if (prev.some((t) => t.id === turn.id)) return prev;
                return [...prev, turn].sort((a, b) => a.sequence - b.sequence);
              });
            }
          } catch (err) {
            console.warn('Error parsing SSE transcript event:', err);
          }
        });

        eventSource.onerror = (err) => {
          console.warn('SSE stream error, polling fallback active:', err);
        };
      } catch (err) {
        console.warn('Could not initialize SSE stream:', err);
      }
    }

    // Polling fallback every 6 seconds
    const pollInterval = setInterval(() => {
      apiClient.listCalls({ limit: 50 }).then((res) => {
        setCalls(res.items);
      }).catch(() => {});
    }, 6000);

    return () => {
      if (eventSource) eventSource.close();
      clearInterval(pollInterval);
    };
  }, [token, selectedCall?.id]);

  // Load transcripts when selected call changes
  useEffect(() => {
    if (!selectedCall) return;
    apiClient.getTranscript(selectedCall.id).then((t) => {
      setTranscripts(t);
    }).catch((e) => {
      console.warn('Could not load transcripts:', e);
    });
  }, [selectedCall?.id]);

  // Clean up supervisor audio room on unmount or call switch
  useEffect(() => {
    return () => {
      if (supervisorRoomRef.current) {
        supervisorRoomRef.current.disconnect();
        supervisorRoomRef.current = null;
      }
    };
  }, []);

  const handleTakeover = async () => {
    if (!selectedCall) return;
    setActionLoading(true);
    try {
      // 1. Call server-authoritative takeover endpoint
      const takeoverRes = await apiClient.takeoverCall(selectedCall.id, 'Supervisor initiated takeover');

      // 2. Connect supervisor to the LiveKit room
      const room = new Room({
        audioCaptureDefaults: {
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      room.on(RoomEvent.TrackSubscribed, (track: Track) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach();
          document.body.appendChild(el);
        }
      });

      await room.connect(takeoverRes.livekit_url, takeoverRes.token);
      await room.localParticipant.setMicrophoneEnabled(true);

      supervisorRoomRef.current = room;
      setIsTakeoverActive(true);
      setShowTakeoverConfirm(false);
      setSelectedCall((prev) => prev ? { ...prev, handoff_state: 'human_active' } : null);
    } catch (e: any) {
      alert(`Takeover failed: ${e.detail || e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleHandback = async () => {
    if (!selectedCall) return;
    setActionLoading(true);
    try {
      await apiClient.handbackCall(selectedCall.id, 'Supervisor returned call to AI');

      if (supervisorRoomRef.current) {
        await supervisorRoomRef.current.disconnect();
        supervisorRoomRef.current = null;
      }
      setIsTakeoverActive(false);
      setSelectedCall((prev) => prev ? { ...prev, handoff_state: 'ai' } : null);
    } catch (e: any) {
      alert(`Handback failed: ${e.detail || e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleEndCall = async () => {
    if (!selectedCall) return;
    setActionLoading(true);
    try {
      await apiClient.endCall(selectedCall.id, 'Ended by supervisor');
      if (supervisorRoomRef.current) {
        await supervisorRoomRef.current.disconnect();
        supervisorRoomRef.current = null;
      }
      setIsTakeoverActive(false);
      setShowEndCallConfirm(false);
      setSelectedCall((prev) => prev ? { ...prev, status: 'completed' } : null);
    } catch (e: any) {
      alert(`End call failed: ${e.detail || e.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleSupervisorMic = async () => {
    if (!supervisorRoomRef.current) return;
    const nextState = !isSupervisorMuted;
    await supervisorRoomRef.current.localParticipant.setMicrophoneEnabled(!nextState);
    setIsSupervisorMuted(nextState);
  };

  // Filtered calls
  const filteredCalls = calls.filter((c) => {
    const matchesSearch =
      (c.participant_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.room_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === 'all' ? true : statusFilter === 'active' ? c.status === 'active' || c.status === 'escalated' : c.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="dashboard-page-container">
      {/* Sticky Takeover Live Ribbon */}
      {isTakeoverActive && selectedCall && (
        <div className="supervisor-live-ribbon">
          <div className="ribbon-content">
            <div className="ribbon-pulse-dot" />
            <span className="ribbon-text">
              <strong>LIVE SUPERVISOR TAKEOVER:</strong> You are actively speaking with{' '}
              <strong>{selectedCall.participant_name || 'Customer'}</strong> in room{' '}
              <span className="saas-mono">{selectedCall.room_name}</span>. The AI is muted.
            </span>
          </div>
          <div className="ribbon-actions">
            <button
              type="button"
              className={`ribbon-mic-btn ${isSupervisorMuted ? 'btn-muted' : ''}`}
              onClick={handleToggleSupervisorMic}
            >
              {isSupervisorMuted ? <MicOff size={15} /> : <Mic size={15} />}
              <span>{isSupervisorMuted ? 'Unmute' : 'Mute'}</span>
            </button>
            <button type="button" className="ribbon-handback-btn" onClick={handleHandback} disabled={actionLoading}>
              <RotateCcw size={15} />
              <span>Hand Back to AI</span>
            </button>
          </div>
        </div>
      )}

      <div className="dashboard-body-grid">
        {/* Left Sidebar: Active Calls List */}
        <aside className="dashboard-sidebar-column">
          <div className="sidebar-inner-card saas-card-glass">
            <div className="sidebar-header-box">
              <div className="sidebar-title-row">
                <h2 className="sidebar-title">Live Call Queue</h2>
                <span className="queue-count-badge">{calls.length}</span>
              </div>

              <div className="search-input-box">
                <Search size={14} className="search-icon" />
                <input
                  type="text"
                  placeholder="Filter by caller or room..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="search-input"
                />
              </div>

              <div className="status-filters-pills">
                {['all', 'active', 'escalated', 'completed'].map((st) => (
                  <button
                    key={st}
                    type="button"
                    className={`filter-pill ${statusFilter === st ? 'filter-pill-active' : ''}`}
                    onClick={() => setStatusFilter(st)}
                  >
                    {st.charAt(0).toUpperCase() + st.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div className="calls-list-scrollable">
              {isLoadingCalls ? (
                <div className="empty-state-card">
                  <span className="btn-spinner" />
                  <p>Connecting to call stream...</p>
                </div>
              ) : filteredCalls.length === 0 ? (
                <div className="empty-state-card">
                  <Headphones size={24} className="empty-icon" />
                  <p>No call sessions matching filter</p>
                </div>
              ) : (
                filteredCalls.map((call) => {
                  const isSelected = selectedCall?.id === call.id;
                  const isEscalated = call.status === 'escalated' || call.handoff_state === 'human_pending';
                  const isLiveTakeover = call.handoff_state === 'human_active';

                  return (
                    <div
                      key={call.id}
                      className={`call-item-card ${isSelected ? 'call-item-selected' : ''}`}
                      onClick={() => setSelectedCall(call)}
                    >
                      <div className="call-item-top">
                        <div className="caller-name-group">
                          <span className="caller-avatar">
                            <User size={14} />
                          </span>
                          <span className="caller-name">{call.participant_name || 'Guest Caller'}</span>
                        </div>
                        <span
                          className={`status-chip-badge ${
                            isLiveTakeover
                              ? 'chip-takeover'
                              : isEscalated
                              ? 'chip-escalated'
                              : call.status === 'active'
                              ? 'chip-active'
                              : 'chip-ended'
                          }`}
                        >
                          {isLiveTakeover ? 'Human Active' : isEscalated ? 'Escalation Alert' : call.status}
                        </span>
                      </div>

                      <div className="call-item-bottom">
                        <span className="room-name-mono saas-mono">{call.room_name}</span>
                        <span className="started-time-sub">
                          {new Date(call.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </aside>

        {/* Right Stage: Call Detail & Live Transcripts */}
        <section className="dashboard-stage-column">
          {selectedCall ? (
            <div className="session-inspector-view">
              {/* Header Plate */}
              <div className="session-header-plate saas-card-glass">
                <div className="plate-top-row">
                  <div className="caller-identity-group">
                    <div className="caller-av-box">
                      <PhoneCall size={20} />
                    </div>
                    <div className="caller-text-group">
                      <div className="caller-name-heading-row">
                        <h2 className="caller-full-name">{selectedCall.participant_name || 'Anonymous Customer'}</h2>
                        <span
                          className={`status-badge-saas ${
                            selectedCall.handoff_state === 'human_active'
                              ? 'badge-saas-takeover'
                              : selectedCall.status === 'escalated'
                              ? 'badge-saas-escalated'
                              : selectedCall.status === 'active'
                              ? 'badge-saas-active'
                              : 'badge-saas-ended'
                          }`}
                        >
                          Handoff: {selectedCall.handoff_state}
                        </span>
                      </div>
                      <span className="room-subtag saas-mono">Room: {selectedCall.room_name}</span>
                    </div>
                  </div>

                  <div className="plate-action-group">
                    {selectedCall.status === 'active' || selectedCall.status === 'escalated' ? (
                      selectedCall.handoff_state === 'human_active' ? (
                        <button
                          type="button"
                          className="btn-handback-action"
                          onClick={handleHandback}
                          disabled={actionLoading}
                        >
                          <RotateCcw size={16} />
                          <span>Return to AI</span>
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="btn-takeover-action"
                          onClick={() => setShowTakeoverConfirm(true)}
                          disabled={actionLoading}
                        >
                          <Radio size={16} />
                          <span>Take Over Call</span>
                        </button>
                      )
                    ) : null}

                    {selectedCall.status === 'active' || selectedCall.status === 'escalated' ? (
                      <button
                        type="button"
                        className="btn-end-session"
                        onClick={() => setShowEndCallConfirm(true)}
                        disabled={actionLoading}
                      >
                        <PhoneOff size={16} />
                        <span>End Call</span>
                      </button>
                    ) : null}
                  </div>
                </div>

                <div className="plate-divider-line" />

                {/* Metadata Row */}
                <div className="session-meta-grid">
                  <div className="meta-data-cell">
                    <span className="cell-label">Session ID</span>
                    <span className="cell-value saas-mono">{selectedCall.id.substring(0, 8)}...</span>
                  </div>
                  <div className="meta-data-cell">
                    <span className="cell-label">Call Duration</span>
                    <span className="cell-value">
                      {selectedCall.duration_seconds != null ? `${selectedCall.duration_seconds}s` : 'In Progress'}
                    </span>
                  </div>
                  <div className="meta-data-cell">
                    <span className="cell-label">Started At</span>
                    <span className="cell-value">
                      {new Date(selectedCall.started_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="meta-data-cell">
                    <span className="cell-label">Summary</span>
                    <span className="cell-value" title={selectedCall.summary || 'Summary generated at call conclusion'}>
                      {selectedCall.summary ? selectedCall.summary.substring(0, 36) + '...' : 'Available after call ends'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Transcript Viewer Stage */}
              <div className="transcript-viewer-card saas-card-glass">
                <div className="transcript-viewer-header">
                  <div className="transcript-title-lockup">
                    <Volume2 size={16} className="transcript-icon" />
                    <h3 className="transcript-title">Real-Time Conversation Transcript</h3>
                  </div>
                  <span className="turns-count">{transcripts.length} Turns Recorded</span>
                </div>

                <div className="transcript-messages-stream">
                  {transcripts.length === 0 ? (
                    <div className="transcript-empty-state">
                      <p>Listening for speech turns...</p>
                    </div>
                  ) : (
                    transcripts.map((turn) => {
                      const isCustomer = turn.role === 'user';
                      const isSupervisor = turn.role === 'supervisor';

                      return (
                        <div
                          key={turn.id}
                          className={`transcript-bubble-row ${
                            isCustomer ? 'row-customer' : isSupervisor ? 'row-supervisor' : 'row-agent'
                          }`}
                        >
                          <div className={`transcript-bubble ${isCustomer ? 'bubble-customer' : isSupervisor ? 'bubble-supervisor' : 'bubble-agent'}`}>
                            <div className="bubble-speaker-header">
                              <span className="speaker-role-label">
                                {isCustomer ? 'Customer' : isSupervisor ? 'Supervisor (You)' : 'Voice AI Agent'}
                              </span>
                              <span className="speaker-time saas-mono">
                                #{turn.sequence} • {new Date(turn.spoken_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                              </span>
                            </div>
                            <p className="bubble-content-text">{turn.content}</p>
                          </div>
                        </div>
                      );
                    })
                  )}
                  <div ref={transcriptEndRef} />
                </div>
              </div>
            </div>
          ) : (
            <div className="no-call-selected-state saas-card-glass">
              <PhoneCall size={36} className="no-call-icon" />
              <h3>No Call Selected</h3>
              <p>Select a live or completed call from the left queue to inspect details and transcripts.</p>
            </div>
          )}
        </section>
      </div>

      {/* Confirmation Modal: Takeover */}
      {showTakeoverConfirm && selectedCall && (
        <div className="modal-backdrop-overlay" role="dialog" aria-modal="true">
          <div className="modal-card saas-card-glass">
            <div className="modal-header">
              <AlertTriangle size={24} className="modal-icon-alert" />
              <h3 className="modal-title">Confirm Voice Takeover</h3>
            </div>
            <p className="modal-message">
              You are about to intervene in the call with <strong>{selectedCall.participant_name || 'Customer'}</strong>.
              The AI assistant will be immediately silenced and your microphone will connect to the room.
            </p>
            <div className="modal-actions-row">
              <button
                type="button"
                className="modal-btn-cancel"
                onClick={() => setShowTakeoverConfirm(false)}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="modal-btn-confirm"
                onClick={handleTakeover}
                disabled={actionLoading}
              >
                {actionLoading ? 'Connecting...' : 'Take Over Call'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal: End Call */}
      {showEndCallConfirm && selectedCall && (
        <div className="modal-backdrop-overlay" role="dialog" aria-modal="true">
          <div className="modal-card saas-card-glass">
            <div className="modal-header">
              <PhoneOff size={24} className="modal-icon-danger" />
              <h3 className="modal-title">Terminate Voice Call</h3>
            </div>
            <p className="modal-message">
              Are you sure you want to end this voice session for room <strong>{selectedCall.room_name}</strong>? Both caller and agent will be disconnected.
            </p>
            <div className="modal-actions-row">
              <button
                type="button"
                className="modal-btn-cancel"
                onClick={() => setShowEndCallConfirm(false)}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="modal-btn-danger"
                onClick={handleEndCall}
                disabled={actionLoading}
              >
                {actionLoading ? 'Ending...' : 'End Call'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
