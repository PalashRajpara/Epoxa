import React, { useState, useEffect, useRef } from 'react';
import {
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  AlertCircle,
  Clock,
  Sparkles,
  Volume2,
  Headphones,
} from 'lucide-react';
import { Room, RoomEvent, Track, RemoteTrack, RemoteParticipant } from 'livekit-client';
import { api } from '../api/client';
import { VoiceVisualizer } from '../components/VoiceVisualizer';
import { CallSession } from '../types';

export const CustomerVoiceView: React.FC = () => {
  const [callerName, setCallerName] = useState('');
  const [callerPhone, setCallerPhone] = useState('');

  const [session, setSession] = useState<CallSession | null>(null);
  const [visualizerState, setVisualizerState] = useState<
    'idle' | 'connecting' | 'listening' | 'agent_speaking' | 'supervisor_takeover' | 'ended'
  >('idle');

  const [isMuted, setIsMuted] = useState(false);
  const [userVolume, setUserVolume] = useState(0); // 0.0 to 1.0 (real-time mic decibel level)
  const [micPermission, setMicPermission] = useState<'prompt' | 'granted' | 'denied'>('prompt');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());
  const [speechStatusText, setSpeechStatusText] = useState('Epoxa Voice Assistant is Ready');

  const recognitionRef = useRef<any>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const isSpeakingRef = useRef<boolean>(false);
  const isMutedRef = useRef<boolean>(false);
  const sessionRef = useRef<CallSession | null>(null);
  const playedSupervisorTurnsRef = useRef<Set<string>>(new Set());
  const isCallEndedRef = useRef<boolean>(false);
  const livekitRoomRef = useRef<Room | null>(null);
  const remoteAudioElementsRef = useRef<HTMLAudioElement[]>([]);

  // Web Audio Analyser references
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Preload browser voices for reliable voice selection
  useEffect(() => {
    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.getVoices();
      };
    }
  }, []);

  // Keep sessionRef updated for listeners
  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  // Keep isMutedRef in sync
  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  // Synchronized clock tick
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, []);

  const getLiveDurationSeconds = () => {
    if (!session?.created_at || session.status === 'completed' || session.status === 'failed') return 0;
    const start = new Date(session.created_at).getTime();
    return Math.max(0, Math.floor((now - start) / 1000));
  };

  // Tab unload listener to immediately terminate call in database if tab closes
  useEffect(() => {
    const handleUnload = () => {
      const activeSession = sessionRef.current;
      if (activeSession && activeSession.status === 'active') {
        const url = `/api/v1/voice/sessions/${activeSession.id}/end`;
        if (navigator.sendBeacon) {
          navigator.sendBeacon(url, JSON.stringify({}));
        } else {
          fetch(url, { method: 'POST', keepalive: true }).catch(() => {});
        }
      }
    };

    window.addEventListener('beforeunload', handleUnload);
    window.addEventListener('pagehide', handleUnload);
    return () => {
      window.removeEventListener('beforeunload', handleUnload);
      window.removeEventListener('pagehide', handleUnload);
    };
  }, []);

  // Poll session state while active to detect supervisor takeover, end call, and play supervisor voice
  useEffect(() => {
    if (!session || session.status === 'completed' || session.status === 'failed') return;

    const interval = setInterval(async () => {
      try {
        const latest = await api.getVoiceSession(session.id);
        if (latest.status === 'completed' && sessionRef.current?.status !== 'completed') {
          handleRemoteCallEnded();
        } else if (latest.status === 'supervisor_takeover') {
          if (visualizerState !== 'supervisor_takeover') {
            setVisualizerState('supervisor_takeover');
            setSpeechStatusText('Live Supervisor is connected to audio stream');
          }

          // Poll for any new supervisor speech turns
          try {
            const supervisorTurns = await api.getSupervisorTurns(session.id);
            for (const turn of supervisorTurns) {
              if (turn.id && !playedSupervisorTurnsRef.current.has(turn.id)) {
                playedSupervisorTurnsRef.current.add(turn.id);
                // Only synthesize / playback audio if supervisor typed a message for AI speech
                // (Live supervisor voice is streamed directly via WebRTC LiveKit)
                if (!turn.is_human && turn.audio_base64) {
                  playSpeechAudio(
                    turn.audio_base64,
                    turn.content || 'Supervisor Message',
                    undefined,
                    true,
                    false,
                    turn.mime_type || 'audio/mpeg',
                    false
                  );
                  break;
                }
              }
            }
          } catch (e) {
            // ignore supervisor turns polling error
          }
        } else if (latest.status === 'active' && visualizerState === 'supervisor_takeover') {
          setVisualizerState('listening');
          setSpeechStatusText('Returned to Epoxa AI • Listening');
        }
      } catch (e) {
        // ignore polling error
      }
    }, visualizerState === 'supervisor_takeover' ? 350 : 1200);

    return () => clearInterval(interval);
  }, [session?.id, visualizerState]);

  // Stop any active playing audio
  const stopCurrentAudio = () => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    isSpeakingRef.current = false;
  };

  const cleanupLivekit = () => {
    if (livekitRoomRef.current) {
      try {
        livekitRoomRef.current.disconnect();
      } catch (e) {}
      livekitRoomRef.current = null;
    }
    remoteAudioElementsRef.current.forEach((el) => {
      try {
        el.pause();
        el.remove();
      } catch (e) {}
    });
    remoteAudioElementsRef.current = [];
  };

  // Clean up Web Audio analysis & microphone stream
  const cleanupAudio = () => {
    cleanupLivekit();
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setUserVolume(0);
  };

  // Play Neural Speech Audio (Deepgram Aura MP3) or Supervisor Real Audio (WebM/MP4) with seamless fallback
  const playSpeechAudio = (
    audioBase64: string | undefined,
    text: string,
    onEnd?: () => void,
    isSupervisor: boolean = false,
    isClosingTurn: boolean = false,
    mimeType: string = 'audio/mpeg',
    isHuman: boolean = false
  ) => {
    stopCurrentAudio();

    if (audioBase64) {
      try {
        const audio = currentAudioRef.current || new Audio();
        currentAudioRef.current = audio;
        audio.src = `data:${mimeType || 'audio/mpeg'};base64,${audioBase64}`;
        audio.currentTime = 0;
        isSpeakingRef.current = true;
        setVisualizerState(isClosingTurn ? 'ended' : isSupervisor ? 'supervisor_takeover' : 'agent_speaking');
        setSpeechStatusText(
          isClosingTurn
            ? text
            : isSupervisor
            ? (isHuman ? `Supervisor (Real Voice): "${text}"` : `Supervisor (AI Voice): "${text}"`)
            : 'Epoxa AI is speaking...'
        );

        audio.onended = () => {
          isSpeakingRef.current = false;
          if (isClosingTurn || isCallEndedRef.current) {
            setVisualizerState('ended');
            setSpeechStatusText('Call completed');
            if (onEnd) onEnd();
            return;
          }
          if (isSupervisor) {
            setVisualizerState('supervisor_takeover');
            setSpeechStatusText('Live Supervisor connected to audio stream');
          } else {
            setVisualizerState('listening');
            setSpeechStatusText('Listening for your voice... Speak naturally');
          }
          if (onEnd) onEnd();
          startListening();
        };

        audio.onerror = (e) => {
          console.warn('Audio playback error', e);
          // If this is real human voice, do NOT read it out using robotic speech synthesis!
          if (isHuman) {
            isSpeakingRef.current = false;
            setVisualizerState('supervisor_takeover');
            setSpeechStatusText('Live Supervisor connected to audio stream');
            if (onEnd) onEnd();
            startListening();
            return;
          }
          playBrowserFallback(text, onEnd, isSupervisor, isClosingTurn);
        };

        audio.play().catch((err) => {
          console.warn('Audio play() rejected', err);
          if (isHuman) {
            isSpeakingRef.current = false;
            setVisualizerState('supervisor_takeover');
            setSpeechStatusText('Live Supervisor connected to audio stream');
            if (onEnd) onEnd();
            startListening();
            return;
          }
          playBrowserFallback(text, onEnd, isSupervisor, isClosingTurn);
        });
        return;
      } catch (e) {
        if (!isHuman) {
          playBrowserFallback(text, onEnd, isSupervisor, isClosingTurn);
        }
        return;
      }
    }

    if (!isHuman) {
      playBrowserFallback(text, onEnd, isSupervisor, isClosingTurn);
    }
  };

  // Fallback browser speech synthesis with preloaded voice cache
  const playBrowserFallback = (
    text: string,
    onEnd?: () => void,
    isSupervisor: boolean = false,
    isClosingTurn: boolean = false
  ) => {
    if (!window.speechSynthesis) {
      if (onEnd) onEnd();
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    if (isSupervisor) {
      const supVoice = voices.find((v) =>
        v.lang.startsWith('en') && (v.name.includes('Daniel') || v.name.includes('Alex') || v.name.includes('Male'))
      ) || voices.find((v) => v.lang.startsWith('en'));
      if (supVoice) utterance.voice = supVoice;
    } else {
      const naturalVoice = voices.find((v) =>
        v.lang.startsWith('en') && (v.name.includes('Samantha') || v.name.includes('Victoria') || v.name.includes('Google US') || v.name.includes('Natural'))
      ) || voices.find((v) => v.lang.startsWith('en'));
      if (naturalVoice) utterance.voice = naturalVoice;
    }

    isSpeakingRef.current = true;
    setVisualizerState(isClosingTurn ? 'ended' : isSupervisor ? 'supervisor_takeover' : 'agent_speaking');
    setSpeechStatusText(isClosingTurn ? text : isSupervisor ? `Supervisor: "${text}"` : 'Epoxa AI is speaking...');

    utterance.onend = () => {
      isSpeakingRef.current = false;
      if (isClosingTurn || isCallEndedRef.current) {
        setVisualizerState('ended');
        setSpeechStatusText('Call completed');
        if (onEnd) onEnd();
        return;
      }
      if (isSupervisor) {
        setVisualizerState('supervisor_takeover');
        setSpeechStatusText('Live Supervisor connected to audio stream');
      } else {
        setVisualizerState('listening');
        setSpeechStatusText('Listening for your voice... Speak naturally');
      }
      if (onEnd) onEnd();
      startListening();
    };

    utterance.onerror = () => {
      isSpeakingRef.current = false;
      if (isClosingTurn || isCallEndedRef.current) {
        setVisualizerState('ended');
        setSpeechStatusText('Call completed');
        if (onEnd) onEnd();
        return;
      }
      setVisualizerState(isSupervisor ? 'supervisor_takeover' : 'listening');
      if (onEnd) onEnd();
      startListening();
    };

    window.speechSynthesis.speak(utterance);
  };

  // Handle remote end call (e.g. supervisor pressed End Call on dashboard)
  const handleRemoteCallEnded = () => {
    isCallEndedRef.current = true;

    // Immediately remove recognition listeners and abort
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onend = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.onresult = null;
        recognitionRef.current.abort();
      } catch (e) {}
      recognitionRef.current = null;
    }
    stopCurrentAudio();
    cleanupAudio();

    setVisualizerState('ended');
    setSpeechStatusText('Call concluded by customer support');
    if (sessionRef.current) {
      sessionRef.current = { ...sessionRef.current, status: 'completed' };
    }
    setSession((prev) => (prev ? { ...prev, status: 'completed' } : null));

    const closingText = 'This call has been concluded by customer support. Thank you for contacting Apex Global Retail. Have a wonderful day!';
    playSpeechAudio(undefined, closingText, undefined, false, true);
  };

  // Start speech recognition
  const startListening = () => {
    if (isCallEndedRef.current || isMutedRef.current || isSpeakingRef.current) return;
    if (!sessionRef.current || (sessionRef.current.status !== 'active' && sessionRef.current.status !== 'initiating')) return;

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) return;

    try {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        if (!isCallEndedRef.current && !isSpeakingRef.current && !isMutedRef.current) {
          setVisualizerState('listening');
          setSpeechStatusText('Listening for your voice... Speak naturally');
        }
      };

      recognition.onresult = async (event: any) => {
        // Guard: Discard transcript turn if user was muted or call ended
        if (isCallEndedRef.current || isMutedRef.current) return;

        const transcript = event.results[0][0].transcript;
        if (!transcript || !sessionRef.current) return;

        setSpeechStatusText(`Processing: "${transcript}"`);
        setVisualizerState('connecting');

        try {
          const res = await api.sendSpeechTurn(sessionRef.current.id, transcript);
          if (res.reply) {
            if (res.reply.toLowerCase().includes('supervisor') && res.reply.toLowerCase().includes('dispatched')) {
              setVisualizerState('supervisor_takeover');
              setSpeechStatusText('Live Supervisor is taking over the audio stream');
            }
            playSpeechAudio(res.audio_base64, res.reply);
          }
        } catch (e: any) {
          setErrorMsg(e.message || 'Error processing speech turn');
          if (!isCallEndedRef.current) {
            setVisualizerState('listening');
            setSpeechStatusText('Listening for your voice... Speak naturally');
            startListening();
          }
        }
      };

      recognition.onerror = () => {
        if (!isCallEndedRef.current && sessionRef.current && sessionRef.current.status === 'active' && !isSpeakingRef.current && !isMutedRef.current) {
          setTimeout(() => {
            if (!isCallEndedRef.current) startListening();
          }, 600);
        }
      };

      recognition.onend = () => {
        if (!isCallEndedRef.current && sessionRef.current && sessionRef.current.status === 'active' && !isSpeakingRef.current && !isMutedRef.current) {
          setTimeout(() => {
            if (!isCallEndedRef.current) startListening();
          }, 600);
        }
      };

      recognition.start();
      recognitionRef.current = recognition;
    } catch (e) {
      // recognition initiation error
    }
  };

  // Start Call
  const startCall = async () => {
    isCallEndedRef.current = false;
    setErrorMsg(null);
    setVisualizerState('connecting');
    setSpeechStatusText('Establishing secure audio connection...');

    // Prime and unlock HTML5 Audio synchronously inside the user click gesture
    if (!currentAudioRef.current) {
      currentAudioRef.current = new Audio();
    }
    const primeAudio = currentAudioRef.current;
    primeAudio.src = "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";
    primeAudio.play().then(() => {
      primeAudio.pause();
      primeAudio.currentTime = 0;
    }).catch(() => {});

    try {
      // 1. Acquire mic stream
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      setMicPermission('granted');

      // 2. Set up Web Audio AnalyserNode for real-time soundwave reactivity
      try {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        const ctx = new AudioCtx();
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 64;
        analyser.smoothingTimeConstant = 0.3;
        const source = ctx.createMediaStreamSource(stream);
        source.connect(analyser);
        audioContextRef.current = ctx;
        analyserRef.current = analyser;

        // Monitor volume loop
        const checkVolume = () => {
          if (!analyserRef.current || isMutedRef.current || isSpeakingRef.current || isCallEndedRef.current) {
            setUserVolume(0);
          } else {
            const data = new Uint8Array(analyserRef.current.frequencyBinCount);
            analyserRef.current.getByteFrequencyData(data);
            let sum = 0;
            for (let i = 0; i < data.length; i++) sum += data[i];
            const avg = sum / data.length;
            if (avg > 10) {
              setUserVolume(Math.min(1, (avg - 10) / 45));
            } else {
              setUserVolume(0);
            }
          }
          animationFrameRef.current = requestAnimationFrame(checkVolume);
        };
        animationFrameRef.current = requestAnimationFrame(checkVolume);
      } catch (e) {
        // audio context setup error
      }

      // 3. Create Session
      const tokenRes = await api.createVoiceToken(
        callerName.trim() || undefined,
        callerPhone.trim() || undefined
      );

      const initialSession: CallSession = {
        id: tokenRes.session_id,
        organization_id: 'apex-retail',
        room_name: tokenRes.room_name,
        status: 'active',
        handoff_state: 'none',
        created_at: tokenRes.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setSession(initialSession);
      playedSupervisorTurnsRef.current.clear();

      // 4. Connect to LiveKit Room for real-time bidirectional WebRTC audio with Supervisor
      if (tokenRes.token && tokenRes.livekit_url) {
        try {
          cleanupLivekit();
          const room = new Room({
            adaptiveStream: true,
            dynacast: true,
            audioCaptureDefaults: {
              autoGainControl: true,
              echoCancellation: true,
              noiseSuppression: true,
            },
          });

          room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication, participant: RemoteParticipant) => {
            if (track.kind === Track.Kind.Audio) {
              const el = track.attach();
              el.id = `livekit-remote-${participant.identity}`;
              el.style.display = 'none';
              document.body.appendChild(el);
              remoteAudioElementsRef.current.push(el);
            }
          });

          room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
            const attached = track.detach();
            attached.forEach((el) => {
              el.remove();
              remoteAudioElementsRef.current = remoteAudioElementsRef.current.filter((item) => item !== el);
            });
          });

          await room.connect(tokenRes.livekit_url, tokenRes.token);
          await room.localParticipant.setMicrophoneEnabled(!isMutedRef.current);
          livekitRoomRef.current = room;
        } catch (lkErr) {
          console.warn('LiveKit WebRTC connect warning:', lkErr);
        }
      }

      // 5. Fetch Deepgram Studio Greeting Audio (Pass session_id to guarantee active status in backend)
      const greetingRes = await api.getGreeting(callerName.trim() || undefined, tokenRes.session_id);
      playSpeechAudio(greetingRes.audio_base64, greetingRes.greeting);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to initialize voice session or access microphone');
      setVisualizerState('idle');
      setSpeechStatusText('Epoxa Voice Assistant is Ready');
      cleanupAudio();
    }
  };

  // End Call locally
  const handleEndCall = async () => {
    isCallEndedRef.current = true;

    // 1. Immediately tear down recognition so onend/onerror can never restart listening
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onend = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.onresult = null;
        recognitionRef.current.abort();
      } catch (e) {}
      recognitionRef.current = null;
    }

    // 2. Stop audio & release microphone hardware tracks
    stopCurrentAudio();
    cleanupAudio();

    // 3. Mark state as ended immediately
    const currentSession = sessionRef.current || session;
    setVisualizerState('ended');
    setSpeechStatusText('Call completed');
    if (sessionRef.current) {
      sessionRef.current = { ...sessionRef.current, status: 'completed' };
    }
    setSession((prev) => (prev ? { ...prev, status: 'completed' } : null));

    // 4. Notify backend
    if (currentSession?.id) {
      try {
        const ended = await api.endVoiceSession(currentSession.id);
        setSession(ended);
      } catch (e: any) {
        // already completed locally
      }
    }
  };

  // Toggle Mute: Completely stops mic audio input, stops speech recognition, and sets waves to 0
  const handleToggleMute = () => {
    const nextMute = !isMuted;
    setIsMuted(nextMute);
    isMutedRef.current = nextMute;

    // 1. Physically disable microphone audio track
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getAudioTracks().forEach((track) => {
        track.enabled = !nextMute;
      });
    }
    if (livekitRoomRef.current) {
      livekitRoomRef.current.localParticipant.setMicrophoneEnabled(!nextMute).catch(() => {});
    }

    // 2. Control recognition & waves
    if (nextMute) {
      setUserVolume(0);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
      }
      setSpeechStatusText('Microphone muted • Live waves stopped');
    } else {
      setSpeechStatusText('Microphone active • Listening');
      startListening();
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div style={{
      height: '100vh',
      maxHeight: '100vh',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '1.25rem 2rem',
      boxSizing: 'border-box',
      background: 'radial-gradient(ellipse at 50% 20%, rgba(99, 102, 241, 0.12) 0%, rgba(7, 9, 14, 0.98) 75%)',
    }}>
      {/* Top Header */}
      <div style={{
        width: '100%',
        maxWidth: '900px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.6rem 1.25rem',
        borderRadius: '0.75rem',
        background: 'rgba(21, 27, 45, 0.6)',
        backdropFilter: 'blur(12px)',
        border: '1px solid var(--border-subtle)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'var(--glow-primary)',
          }}>
            <Headphones size={18} color="#ffffff" />
          </div>
          <div>
            <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#ffffff' }}>
              Apex Global Retail • Customer Voice
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Direct Voice Line • AI Customer Support
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {session && session.status === 'active' && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.35rem 0.75rem',
              borderRadius: '999px',
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#34d399',
              fontSize: '0.8rem',
              fontWeight: 600,
            }}>
              <span style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: '#10b981',
                boxShadow: '0 0 8px #10b981',
              }} />
              <Clock size={13} />
              <span style={{ fontFamily: 'var(--font-mono)' }}>{formatSeconds(getLiveDurationSeconds())}</span>
            </div>
          )}

          <div style={{
            fontSize: '0.75rem',
            padding: '0.3rem 0.65rem',
            borderRadius: '0.4rem',
            background: isMuted ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255, 255, 255, 0.05)',
            color: isMuted ? '#fca5a5' : 'var(--text-secondary)',
            border: isMuted ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid var(--border-subtle)',
            fontWeight: isMuted ? 600 : 400,
          }}>
            {isMuted ? 'MIC MUTED' : 'Deepgram Neural HD'}
          </div>
        </div>
      </div>

      {/* Error Alert if any */}
      {errorMsg && (
        <div style={{
          maxWidth: '650px',
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          padding: '0.65rem 1rem',
          borderRadius: '0.5rem',
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#fca5a5',
          fontSize: '0.82rem',
        }}>
          <AlertCircle size={15} style={{ flexShrink: 0 }} />
          <span style={{ flex: 1 }}>{errorMsg}</span>
          <button
            onClick={() => setErrorMsg(null)}
            style={{ background: 'transparent', border: 'none', color: '#fca5a5', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      )}

      {/* Center Stage: Pre-Call Form OR In-Call Voice Orb */}
      {!session || session.status === 'completed' ? (
        /* Pre-Call Setup Form */
        <div className="card" style={{
          maxWidth: '460px',
          width: '100%',
          padding: '2rem',
          borderRadius: '1.25rem',
          textAlign: 'center',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6)',
          border: '1px solid var(--border-subtle)',
        }}>
          <div style={{ marginBottom: '1.5rem' }}>
            <VoiceVisualizer state="idle" />
            <h1 style={{ fontSize: '1.4rem', color: '#ffffff', marginTop: '1rem', marginBottom: '0.3rem' }}>
              Connect with Epoxa AI
            </h1>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Studio-quality, human-grade voice support. Speak naturally into your device.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginBottom: '1.5rem', textAlign: 'left' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
                Your Name (Optional)
              </label>
              <input
                id="customer-name-input"
                type="text"
                placeholder="e.g. Sarah Connor"
                value={callerName}
                onChange={(e) => setCallerName(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.65rem 0.85rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-main)',
                  color: '#ffffff',
                  fontSize: '0.88rem',
                  outline: 'none',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
                Phone Number (Optional)
              </label>
              <input
                id="customer-phone-input"
                type="tel"
                placeholder="e.g. +1 555-019-2834"
                value={callerPhone}
                onChange={(e) => setCallerPhone(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.65rem 0.85rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-main)',
                  color: '#ffffff',
                  fontSize: '0.88rem',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          <button
            id="start-call-btn"
            onClick={startCall}
            className="btn btn-primary"
            style={{
              width: '100%',
              padding: '0.85rem',
              fontSize: '1rem',
              borderRadius: '0.6rem',
              gap: '0.6rem',
            }}
          >
            <Phone size={18} />
            Start Voice Support Call
          </button>

          {session?.summary && (
            <div style={{
              marginTop: '1.25rem',
              padding: '0.75rem',
              borderRadius: '0.5rem',
              background: 'rgba(99, 102, 241, 0.08)',
              border: '1px solid rgba(99, 102, 241, 0.2)',
              fontSize: '0.78rem',
              textAlign: 'left',
            }}>
              <span style={{ fontWeight: 700, color: '#a5b4fc' }}>Previous Call Summary: </span>
              <span style={{ color: 'var(--text-secondary)' }}>{session.summary.summary}</span>
            </div>
          )}
        </div>
      ) : (
        /* In-Call Active Centerpiece */
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '1.25rem',
          textAlign: 'center',
        }}>
          {/* Glowing Voice Orb with Real-time Volume & Mute Awareness */}
          <div style={{ position: 'relative' }}>
            <VoiceVisualizer
              state={visualizerState}
              isMuted={isMuted}
              volume={userVolume}
            />
          </div>

          {/* Turn status indicator */}
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.4rem',
          }}>
            <h2 style={{ fontSize: '1.3rem', color: '#ffffff', fontWeight: 600 }}>
              {callerName ? `${callerName} • Voice Call Active` : 'Voice Call with Epoxa AI'}
            </h2>

            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.45rem 1rem',
              borderRadius: '999px',
              background: isMuted
                ? 'rgba(239, 68, 68, 0.15)'
                : visualizerState === 'agent_speaking'
                ? 'rgba(99, 102, 241, 0.15)'
                : visualizerState === 'supervisor_takeover'
                ? 'rgba(245, 158, 11, 0.15)'
                : 'rgba(16, 185, 129, 0.12)',
              border: `1px solid ${
                isMuted
                  ? 'rgba(239, 68, 68, 0.35)'
                  : visualizerState === 'agent_speaking'
                  ? 'rgba(99, 102, 241, 0.35)'
                  : visualizerState === 'supervisor_takeover'
                  ? 'rgba(245, 158, 11, 0.35)'
                  : 'rgba(16, 185, 129, 0.3)'
              }`,
              color: isMuted
                ? '#fca5a5'
                : visualizerState === 'agent_speaking'
                ? '#a5b4fc'
                : visualizerState === 'supervisor_takeover'
                ? '#fbbf24'
                : '#34d399',
              fontSize: '0.85rem',
              fontWeight: 500,
            }}>
              <Volume2 size={15} />
              <span>{speechStatusText}</span>
            </div>
          </div>

          {/* Controls: Mute & End Call */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1.5rem',
            marginTop: '0.5rem',
          }}>
            <button
              id="mute-mic-btn"
              onClick={handleToggleMute}
              className={isMuted ? "btn btn-danger" : "btn btn-secondary"}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.6rem',
                padding: '0.85rem 1.6rem',
                borderRadius: '999px',
                fontSize: '0.95rem',
                fontWeight: 600,
                borderColor: isMuted ? 'rgba(239, 68, 68, 0.7)' : 'var(--border-subtle)',
                background: isMuted ? 'rgba(239, 68, 68, 0.25)' : 'var(--bg-card)',
                boxShadow: isMuted ? '0 0 18px rgba(239, 68, 68, 0.35)' : 'none',
                cursor: 'pointer',
                color: isMuted ? '#fca5a5' : '#ffffff',
                transition: 'all 0.2s ease',
              }}
              title={isMuted ? 'Unmute Microphone' : 'Mute Microphone'}
            >
              {isMuted ? <MicOff size={20} color="#f87171" /> : <Mic size={20} color="#ffffff" />}
              <span>{isMuted ? 'Unmute Mic' : 'Mute Mic'}</span>
            </button>

            <button
              id="end-call-btn"
              onClick={handleEndCall}
              className="btn btn-danger"
              style={{
                padding: '0.85rem 2.2rem',
                borderRadius: '999px',
                fontSize: '1rem',
                fontWeight: 600,
                boxShadow: '0 8px 24px rgba(239, 68, 68, 0.35)',
                gap: '0.6rem',
              }}
            >
              <PhoneOff size={20} />
              End Call
            </button>
          </div>
        </div>
      )}

      {/* Footer Note */}
      <div style={{
        textAlign: 'center',
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
        maxWidth: '600px',
      }}>
        Voice calls are isolated and retention-managed for enterprise privacy.
        Official Apex Global Retail Customer Service Line.
      </div>
    </div>
  );
};
