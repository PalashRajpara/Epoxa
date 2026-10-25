import React, { useState, useEffect, useRef } from 'react';
import {
  Radio,
  User,
  Clock,
  PhoneOff,
  UserCheck,
  RotateCcw,
  RefreshCw,
  AlertTriangle,
  FileText,
  ShieldAlert,
  Headphones,
  CheckCircle2,
  Mic,
  MicOff,
  Send,
  Volume2,
} from 'lucide-react';
import { Room, RoomEvent, Track, RemoteTrack, RemoteParticipant } from 'livekit-client';
import { api } from '../../api/client';
import { CallSession, TranscriptTurn } from '../../types';
import { StatusBadge } from '../../components/Badge';

// Helper to choose supported audio mime type for real human voice recording
const getAudioMimeType = (): string => {
  if (typeof MediaRecorder === 'undefined') return 'audio/webm';
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
  ];
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return 'audio/webm';
};

const blobToBase64 = (blob: Blob): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const dataUrl = reader.result as string;
      const base64 = dataUrl.split(',')[1] || '';
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
};

export const ActiveCallsList: React.FC = () => {
  const [calls, setCalls] = useState<CallSession[]>([]);
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [transcripts, setTranscripts] = useState<TranscriptTurn[]>([]);
  const [now, setNow] = useState(Date.now());
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  // Supervisor speaking & mic mute controls
  const [supervisorMuted, setSupervisorMuted] = useState(false);
  const [supervisorMicActive, setSupervisorMicActive] = useState(false);
  const [supervisorSpeechInput, setSupervisorSpeechInput] = useState('');
  const [sendingSpeech, setSendingSpeech] = useState(false);
  const [speechFeedback, setSpeechFeedback] = useState<string | null>(null);

  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const supervisorRecognitionRef = useRef<any>(null);
  const supervisorLivekitRoomRef = useRef<Room | null>(null);
  const supervisorRemoteAudioRef = useRef<HTMLAudioElement[]>([]);
  const supervisorMutedRef = useRef(false);

  useEffect(() => {
    supervisorMutedRef.current = supervisorMuted;
  }, [supervisorMuted]);

  // Clean up supervisor mic and recognition on unmount
  useEffect(() => {
    return () => {
      stopSupervisorLiveAudio();
    };
  }, []);

  // 500ms interval to update live elapsed call timers synchronized with customer view
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, []);

  // Poll active calls every 2 seconds
  const fetchCalls = async () => {
    try {
      const res = await api.getActiveCalls();
      setCalls(res);
      // Auto-select first call if none selected or selected call no longer in active list
      if (res.length > 0) {
        setSelectedCallId((prev) => (res.some((c) => c.id === prev) ? prev : res[0].id));
      } else {
        setSelectedCallId(null);
        setTranscripts([]);
      }
    } catch (e) {
      // ignore poll error
    }
  };

  useEffect(() => {
    fetchCalls();
    const interval = setInterval(fetchCalls, 2000);
    return () => clearInterval(interval);
  }, []);

  // Poll transcripts for selected call
  useEffect(() => {
    if (!selectedCallId) {
      setTranscripts([]);
      return;
    }

    const fetchTranscripts = async () => {
      try {
        const res = await api.getTranscripts(selectedCallId);
        setTranscripts(res);
      } catch (e) {
        // ignore poll error
      }
    };

    fetchTranscripts();
    const interval = setInterval(fetchTranscripts, 1500);
    return () => clearInterval(interval);
  }, [selectedCallId]);

  // Auto-scroll transcripts to bottom
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts]);

  const selectedCall = calls.find((c) => c.id === selectedCallId) || null;

  // Format live duration synchronized to seconds
  const getLiveDuration = (createdAt: string) => {
    const start = new Date(createdAt).getTime();
    const diffSec = Math.max(0, Math.floor((now - start) / 1000));
    const m = Math.floor(diffSec / 60);
    const s = diffSec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Automatically acquire and stream supervisor audio via LiveKit whenever a call enters supervisor_takeover
  useEffect(() => {
    if (selectedCall?.status === 'supervisor_takeover') {
      if (!supervisorLivekitRoomRef.current) {
        startSupervisorLiveAudio();
      }
    } else {
      stopSupervisorLiveAudio();
    }
  }, [selectedCall?.status, selectedCall?.id]);

  // Start supervisor live microphone audio stream for realtime bidirectional WebRTC voice
  const startSupervisorLiveAudio = async (overrideToken?: string, overrideUrl?: string) => {
    if (!selectedCallId) return;
    try {
      // 1. Get LiveKit room token
      let token = overrideToken;
      let livekitUrl = overrideUrl;
      if (!token) {
        const tokenRes = await api.getSupervisorToken(selectedCallId);
        token = tokenRes.token;
        livekitUrl = tokenRes.livekit_url;
      }

      if (!token) {
        setSpeechFeedback('Unable to acquire LiveKit room token.');
        return;
      }

      // Cleanup any previous room connection
      stopSupervisorLiveAudio();

      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        audioCaptureDefaults: {
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      // When customer speaks, attach remote track so supervisor hears customer in real-time
      room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication, participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach();
          el.id = `livekit-customer-audio-${participant.identity}`;
          el.style.display = 'none';
          document.body.appendChild(el);
          supervisorRemoteAudioRef.current.push(el);
          setSpeechFeedback('Customer voice connected. Two-way live voice active!');
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
        const attached = track.detach();
        attached.forEach((el) => {
          el.remove();
          supervisorRemoteAudioRef.current = supervisorRemoteAudioRef.current.filter((item) => item !== el);
        });
      });

      await room.connect(livekitUrl || 'wss://epoxa-dnmkm636.livekit.cloud', token);
      await room.localParticipant.setMicrophoneEnabled(!supervisorMutedRef.current);
      supervisorLivekitRoomRef.current = room;
      setSupervisorMicActive(true);
      setSpeechFeedback('Two-way live voice connected. Speak naturally into your mic.');

      // Setup optional browser SpeechRecognition to transcribe supervisor speech into live transcript stream
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = async (event: any) => {
          if (supervisorMutedRef.current || !selectedCallId) return;
          const lastResult = event.results[event.results.length - 1];
          if (lastResult.isFinal) {
            const spoken = lastResult[0].transcript;
            if (spoken && spoken.trim()) {
              try {
                await api.sendSupervisorTurn(selectedCallId, spoken.trim(), 'LIVE_HUMAN_WEBRTC', 'audio/webrtc');
                const updated = await api.getTranscripts(selectedCallId);
                setTranscripts(updated);
              } catch (e) {}
            }
          }
        };

        recognition.onend = () => {
          if (supervisorLivekitRoomRef.current && !supervisorMutedRef.current) {
            try { recognition.start(); } catch (e) {}
          }
        };

        recognition.start();
        supervisorRecognitionRef.current = recognition;
      }
    } catch (e: any) {
      console.warn('LiveKit supervisor audio setup error:', e);
      setSpeechFeedback('Could not connect two-way voice stream: ' + (e.message || 'Check microphone permission.'));
    }
  };

  // Stop supervisor live audio & disconnect LiveKit room
  const stopSupervisorLiveAudio = () => {
    if (supervisorRecognitionRef.current) {
      try {
        supervisorRecognitionRef.current.onend = null;
        supervisorRecognitionRef.current.onerror = null;
        supervisorRecognitionRef.current.abort();
      } catch (e) {}
      supervisorRecognitionRef.current = null;
    }
    if (supervisorLivekitRoomRef.current) {
      try {
        supervisorLivekitRoomRef.current.disconnect();
      } catch (e) {}
      supervisorLivekitRoomRef.current = null;
    }
    supervisorRemoteAudioRef.current.forEach((el) => {
      try { el.pause(); el.remove(); } catch (e) {}
    });
    supervisorRemoteAudioRef.current = [];
    setSupervisorMicActive(false);
  };

  // Supervisor Mute / Unmute Toggle
  const handleToggleSupervisorMute = async () => {
    const nextMuted = !supervisorMuted;
    setSupervisorMuted(nextMuted);
    supervisorMutedRef.current = nextMuted;

    if (supervisorLivekitRoomRef.current) {
      await supervisorLivekitRoomRef.current.localParticipant.setMicrophoneEnabled(!nextMuted).catch(() => {});
    }

    if (nextMuted) {
      if (supervisorRecognitionRef.current) {
        try { supervisorRecognitionRef.current.abort(); } catch (e) {}
      }
      setSpeechFeedback('Microphone MUTED. Customer cannot hear you.');
    } else {
      if (supervisorRecognitionRef.current) {
        try { supervisorRecognitionRef.current.start(); } catch (e) {}
      }
      setSpeechFeedback('Microphone UNMUTED. Real human voice streams to customer.');
    }
  };

  // Send supervisor speech turn to customer (typed AI voice text)
  const handleSendSupervisorSpeech = async (
    speechText: string,
    audioBase64?: string,
    mimeType?: string
  ) => {
    if (!selectedCall || (!speechText.trim() && !audioBase64) || sendingSpeech) return;
    setSendingSpeech(true);
    const isHuman = Boolean(audioBase64);
    setSpeechFeedback(
      isHuman
        ? `Transcribed human voice: "${speechText}"`
        : `Synthesizing AI voice for: "${speechText}"...`
    );

    try {
      await api.sendSupervisorTurn(selectedCall.id, speechText.trim(), audioBase64, mimeType);
      if (!isHuman) {
        setSupervisorSpeechInput('');
      }
      setSpeechFeedback(
        isHuman
          ? `Transcribed: "${speechText}"`
          : `AI Voice Broadcasted: "${speechText}"`
      );
      const updated = await api.getTranscripts(selectedCall.id);
      setTranscripts(updated);
    } catch (err: any) {
      setSpeechFeedback(`Failed to broadcast: ${err.message || 'Error'}`);
    } finally {
      setSendingSpeech(false);
    }
  };

  // Handoff toggle
  const handleToggleHandoff = async () => {
    if (!selectedCall) return;
    setActionLoading(true);
    setActionMsg(null);

    try {
      if (selectedCall.status === 'supervisor_takeover') {
        // Hand back to AI
        await api.handbackCall(selectedCall.id, 'Supervisor returned control to Epoxa AI');
        stopSupervisorLiveAudio();
        setActionMsg('Call returned to Epoxa AI control.');
      } else {
        // Take over
        const res = await api.takeoverCall(selectedCall.id, 'Supervisor initiated live takeover');
        setActionMsg('Takeover active. Two-way voice established with customer.');
        await startSupervisorLiveAudio(res.token, res.livekit_url);
      }
      await fetchCalls();
    } catch (err: any) {
      alert(err.message || 'Handoff action failed');
    } finally {
      setActionLoading(false);
    }
  };

  // Supervisor Force End Call
  const handleEndCall = async () => {
    if (!selectedCall) return;
    if (!window.confirm(`Are you sure you want to end the call for ${selectedCall.metadata?.customer_name || 'Customer'}?`)) {
      return;
    }

    const endingCallId = selectedCall.id;
    setActionLoading(true);

    stopSupervisorLiveAudio();

    try {
      await api.forceEndCall(endingCallId);
      setActionMsg('Call ended successfully.');
      setCalls((prev) => prev.filter((c) => c.id !== endingCallId));
      setSelectedCallId((prev) => (prev === endingCallId ? null : prev));
      setTranscripts([]);
      await fetchCalls();
    } catch (err: any) {
      alert(err.message || 'Failed to end call');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      gap: '1.25rem',
      height: '100%',
      maxHeight: '100%',
      overflow: 'hidden',
      boxSizing: 'border-box',
    }}>
      {/* LEFT PANEL: Active Calls List (Master) */}
      <div style={{
        width: '340px',
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        height: '100%',
        overflow: 'hidden',
      }}>
        {/* List Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
          padding: '0.2rem 0',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: calls.length > 0 ? '#10b981' : '#64748b',
              boxShadow: calls.length > 0 ? '0 0 10px #10b981' : 'none',
              display: 'inline-block',
            }} />
            <h2 style={{ fontSize: '1.05rem', color: '#ffffff', fontWeight: 700 }}>
              Live Calls ({calls.length})
            </h2>
          </div>
          <button
            onClick={fetchCalls}
            className="btn btn-secondary"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem', gap: '0.3rem' }}
          >
            <RefreshCw size={12} />
            Refresh
          </button>
        </div>

        {/* Calls List or Empty State */}
        {calls.length === 0 ? (
          <div className="card" style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            padding: '2rem 1.25rem',
            background: 'var(--bg-surface)',
          }}>
            <Radio size={28} color="#64748b" style={{ marginBottom: '0.75rem' }} />
            <h3 style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.3rem' }}>
              No Active Calls
            </h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
              When a customer calls via http://localhost:5173, their session appears here in real-time.
            </p>
          </div>
        ) : (
          <div style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.65rem',
            paddingRight: '0.25rem',
          }}>
            {calls.map((call) => {
              const isSelected = call.id === selectedCallId;
              const isEscalated = call.status === 'escalated';
              const isTakenOver = call.status === 'supervisor_takeover';

              return (
                <div
                  key={call.id}
                  onClick={() => setSelectedCallId(call.id)}
                  className="card"
                  style={{
                    padding: '0.9rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    border: isSelected
                      ? '1px solid var(--accent-primary)'
                      : isEscalated
                      ? '1px solid rgba(239, 68, 68, 0.4)'
                      : isTakenOver
                      ? '1px solid rgba(245, 158, 11, 0.4)'
                      : '1px solid var(--border-subtle)',
                    background: isSelected ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                    boxShadow: isSelected ? '0 0 15px rgba(99, 102, 241, 0.2)' : 'none',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontWeight: 600, color: '#ffffff', fontSize: '0.88rem' }}>
                      <User size={15} color={isSelected ? '#818cf8' : '#94a3b8'} />
                      <span>{call.metadata?.customer_name || 'Guest Caller'}</span>
                    </div>
                    <StatusBadge status={call.status} />
                  </div>

                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '0.75rem',
                    color: 'var(--text-muted)',
                  }}>
                    <span>{new Date(call.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    <span style={{
                      color: '#34d399',
                      fontWeight: 600,
                      fontFamily: 'var(--font-mono)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.3rem',
                    }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }} />
                      {getLiveDuration(call.created_at)}
                    </span>
                  </div>

                  {isEscalated && (
                    <div style={{
                      padding: '0.3rem 0.5rem',
                      borderRadius: '0.3rem',
                      background: 'rgba(239, 68, 68, 0.12)',
                      color: '#f87171',
                      fontSize: '0.72rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.3rem',
                      fontWeight: 600,
                    }}>
                      <AlertTriangle size={12} />
                      Manager assistance requested
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* RIGHT PANEL: Live Details & Real-Time Transcript Stream (Beside the List) */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem',
        height: '100%',
        overflow: 'hidden',
      }}>
        {selectedCall ? (
          <>
            {/* Call Detail Header Card */}
            <div className="card" style={{
              padding: '1rem 1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.85rem',
              flexShrink: 0,
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
            }}>
              {/* Top Row: Customer Info & Status */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <div style={{
                    width: '38px',
                    height: '38px',
                    borderRadius: '10px',
                    background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <Headphones size={20} color="#ffffff" />
                  </div>
                  <div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>
                      {selectedCall.metadata?.customer_name || 'Guest Caller'}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Room: <span style={{ fontFamily: 'var(--font-mono)' }}>{selectedCall.room_name}</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <StatusBadge status={selectedCall.status} />
                </div>
              </div>

              {/* Middle Row: Call Timers & Details Badges */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '0.75rem',
                background: 'var(--bg-main)',
                padding: '0.65rem 1rem',
                borderRadius: '0.5rem',
                border: '1px solid var(--border-subtle)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem' }}>
                  <Clock size={15} color="#818cf8" />
                  <div>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem', display: 'block' }}>When Called</span>
                    <strong style={{ color: 'var(--text-primary)' }}>
                      {new Date(selectedCall.created_at).toLocaleTimeString()}
                    </strong>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem' }}>
                  <Radio size={15} color="#10b981" />
                  <div>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem', display: 'block' }}>Call Live Time</span>
                    <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                      {getLiveDuration(selectedCall.created_at)}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Action Buttons: Handoff Toggle & End Call */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                {/* Hand Off / Hand On Button */}
                <button
                  id="handoff-toggle-btn"
                  onClick={handleToggleHandoff}
                  disabled={actionLoading}
                  className="btn"
                  style={{
                    flex: 1,
                    padding: '0.65rem 1rem',
                    fontSize: '0.88rem',
                    gap: '0.5rem',
                    backgroundColor: selectedCall.status === 'supervisor_takeover' ? '#4f46e5' : '#f59e0b',
                    color: '#ffffff',
                    fontWeight: 600,
                    borderRadius: '0.5rem',
                    border: 'none',
                    boxShadow: selectedCall.status === 'supervisor_takeover'
                      ? '0 0 15px rgba(79, 70, 229, 0.4)'
                      : '0 0 15px rgba(245, 158, 11, 0.35)',
                  }}
                >
                  {selectedCall.status === 'supervisor_takeover' ? (
                    <>
                      <RotateCcw size={16} />
                      Hand On (Return Call to AI)
                    </>
                  ) : (
                    <>
                      <UserCheck size={16} />
                      Hand Off (Take Over Call)
                    </>
                  )}
                </button>

                {/* Force End Call Button */}
                <button
                  id="end-call-btn"
                  onClick={handleEndCall}
                  disabled={actionLoading}
                  className="btn btn-danger"
                  style={{
                    padding: '0.65rem 1.25rem',
                    fontSize: '0.88rem',
                    gap: '0.45rem',
                    borderRadius: '0.5rem',
                    fontWeight: 600,
                  }}
                >
                  <PhoneOff size={16} />
                  End Call
                </button>
              </div>

              {actionMsg && (
                <div style={{
                  fontSize: '0.78rem',
                  color: '#34d399',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                }}>
                  <CheckCircle2 size={13} />
                  <span>{actionMsg}</span>
                </div>
              )}

              {/* Supervisor Live Voice & Broadcast Console */}
              {selectedCall.status === 'supervisor_takeover' ? (
                <div style={{
                  marginTop: '0.2rem',
                  padding: '0.85rem 1rem',
                  borderRadius: '0.5rem',
                  background: 'rgba(79, 70, 229, 0.1)',
                  border: '1px solid rgba(79, 70, 229, 0.35)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.75rem',
                }}>
                  {/* Console Header */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Volume2 size={16} color="#818cf8" />
                      <span style={{ fontSize: '0.84rem', fontWeight: 700, color: '#ffffff' }}>
                        Supervisor Voice Console
                      </span>
                      <span style={{
                        fontSize: '0.68rem',
                        padding: '0.15rem 0.45rem',
                        borderRadius: '0.25rem',
                        background: supervisorMuted ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        color: supervisorMuted ? '#f87171' : '#34d399',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                      }}>
                        <span style={{
                          width: '6px',
                          height: '6px',
                          borderRadius: '50%',
                          background: supervisorMuted ? '#ef4444' : '#10b981',
                          boxShadow: supervisorMuted ? 'none' : '0 0 6px #10b981',
                        }} />
                        {supervisorMuted ? 'MIC MUTED' : 'REALTIME VOICE LIVE'}
                      </span>
                    </div>

                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      {supervisorMuted
                        ? 'Microphone is muted'
                        : 'Speak naturally into mic • Customer hears your voice in realtime'}
                    </span>
                  </div>

                  {/* Exactly 3 Things: 1st Mic Mute/Unmute, 2nd Text Input Box, 3rd Speak AI Send Button */}
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    {/* 1st: Mic Mute / Unmute Button */}
                    <button
                      id="supervisor-mute-mic-btn"
                      type="button"
                      onClick={handleToggleSupervisorMute}
                      style={{
                        padding: '0.45rem 0.85rem',
                        fontSize: '0.78rem',
                        borderRadius: '0.4rem',
                        border: supervisorMuted ? '1px solid rgba(239, 68, 68, 0.6)' : '1px solid rgba(16, 185, 129, 0.6)',
                        background: supervisorMuted ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        color: supervisorMuted ? '#fca5a5' : '#34d399',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        fontWeight: 600,
                        flexShrink: 0,
                        transition: 'all 0.15s ease',
                      }}
                      title={supervisorMuted ? 'Unmute your microphone' : 'Mute your microphone'}
                    >
                      {supervisorMuted ? (
                        <>
                          <MicOff size={14} color="#f87171" />
                          Unmute Mic
                        </>
                      ) : (
                        <>
                          <Mic size={14} color="#34d399" />
                          Mute Mic
                        </>
                      )}
                    </button>

                    {/* 2nd: Text Input Box */}
                    <div style={{ flex: 1, display: 'flex', gap: '0.4rem' }}>
                      <input
                        type="text"
                        placeholder={supervisorMuted ? "Mic is muted. Unmute or type here for AI speech..." : "Speak naturally into mic or type here for AI speech..."}
                        value={supervisorSpeechInput}
                        onChange={(e) => setSupervisorSpeechInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSendSupervisorSpeech(supervisorSpeechInput);
                          }
                        }}
                        disabled={sendingSpeech}
                        style={{
                          flex: 1,
                          padding: '0.45rem 0.75rem',
                          fontSize: '0.82rem',
                          background: 'var(--bg-main)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: '0.4rem',
                          color: '#ffffff',
                          outline: 'none',
                        }}
                      />

                      {/* 3rd: Speak AI Send Button */}
                      <button
                        type="button"
                        onClick={() => handleSendSupervisorSpeech(supervisorSpeechInput)}
                        disabled={sendingSpeech || !supervisorSpeechInput.trim()}
                        className="btn btn-primary"
                        style={{
                          padding: '0.45rem 0.85rem',
                          fontSize: '0.78rem',
                          gap: '0.35rem',
                          borderRadius: '0.4rem',
                          flexShrink: 0,
                          fontWeight: 600,
                        }}
                        title="Synthesize high-quality AI speech for typed message and broadcast to customer"
                      >
                        <Send size={13} />
                        {sendingSpeech ? 'Transmitting...' : 'Speak (AI)'}
                      </button>
                    </div>
                  </div>

                  {speechFeedback && (
                    <div style={{ fontSize: '0.74rem', color: '#818cf8', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      <CheckCircle2 size={12} />
                      <span>{speechFeedback}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{
                  fontSize: '0.74rem',
                  color: 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.2rem 0',
                }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#6366f1' }} />
                  <span>Epoxa AI is handling customer audio. Click <strong>Hand Off (Take Over Call)</strong> above to speak live to this customer.</span>
                </div>
              )}
            </div>

            {/* Live Conversation Transcript Stream (Scrollable) */}
            <div className="card" style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              padding: '1rem',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '0.65rem',
                borderBottom: '1px solid var(--border-subtle)',
                marginBottom: '0.75rem',
                flexShrink: 0,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#ffffff', fontWeight: 600, fontSize: '0.88rem' }}>
                  <FileText size={15} color="#818cf8" />
                  <span>Live Conversational Transcript Stream</span>
                </div>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  Auto-Updating • 30-Day Retention Protected
                </span>
              </div>

              {/* Transcript Dialogue Bubbles */}
              <div style={{
                flex: 1,
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
                paddingRight: '0.4rem',
              }}>
                {transcripts.length === 0 ? (
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                    color: 'var(--text-muted)',
                    fontSize: '0.82rem',
                    textAlign: 'center',
                  }}>
                    Listening for conversation dialogue turns in room audio...
                  </div>
                ) : (
                  transcripts.map((turn, i) => {
                    const isCustomer = turn.speaker === 'customer';
                    const isSupervisor = turn.speaker === 'supervisor';

                    return (
                      <div
                        key={turn.id || i}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: isCustomer ? 'flex-end' : 'flex-start',
                        }}
                      >
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.4rem',
                          marginBottom: '0.2rem',
                        }}>
                          <span style={{
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            color: isCustomer ? '#a5b4fc' : isSupervisor ? '#fbbf24' : '#34d399',
                          }}>
                            {isCustomer ? 'Customer' : isSupervisor ? 'Supervisor (You)' : 'Epoxa AI'}
                          </span>
                          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                            {turn.created_at ? new Date(turn.created_at).toLocaleTimeString() : ''}
                          </span>
                        </div>

                        <div style={{
                          maxWidth: '82%',
                          padding: '0.65rem 0.9rem',
                          borderRadius: '0.65rem',
                          fontSize: '0.85rem',
                          lineHeight: 1.45,
                          backgroundColor: isCustomer
                            ? 'var(--accent-primary)'
                            : isSupervisor
                            ? 'rgba(245, 158, 11, 0.15)'
                            : 'var(--bg-main)',
                          color: '#ffffff',
                          border: isCustomer
                            ? 'none'
                            : isSupervisor
                            ? '1px solid rgba(245, 158, 11, 0.3)'
                            : '1px solid var(--border-subtle)',
                        }}>
                          {turn.content}
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={transcriptEndRef} />
              </div>
            </div>
          </>
        ) : (
          /* Empty selection state */
          <div className="card" style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            padding: '2.5rem',
            background: 'var(--bg-surface)',
          }}>
            <FileText size={36} color="#64748b" style={{ marginBottom: '1rem' }} />
            <h3 style={{ fontSize: '1.05rem', color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
              Select a Live Call
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', maxWidth: '380px' }}>
              Select any live customer call from the list on the left to monitor the real-time transcript stream, live call duration, and take over or end the call.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
