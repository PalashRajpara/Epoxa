import {
  CallSession,
  TranscriptTurn,
  SupportTicket,
  SupervisorProfile,
  VoiceTokenResponse,
  HealthStatus,
  PaginatedResult,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('epoxa_supervisor_token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('epoxa_supervisor_token', token);
    } else {
      localStorage.removeItem('epoxa_supervisor_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const url = endpoint.startsWith('http') || endpoint.startsWith('/health')
      ? endpoint
      : `${BASE_URL}${endpoint}`;

    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
      let errorMsg = `Request failed (${response.status})`;
      try {
        const errorJson = await response.json();
        if (errorJson.error?.message) {
          errorMsg = errorJson.error.message;
        } else if (errorJson.detail) {
          errorMsg = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch (e) {
        // use default error message
      }
      throw new Error(errorMsg);
    }

    return response.json();
  }

  // Health
  async getHealth(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/health/ready');
  }

  // Supervisor Auth
  async login(email: string, password: string): Promise<{ access_token: string; user: SupervisorProfile }> {
    const res = await this.request<{ access_token: string; user: SupervisorProfile }>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }
    );
    this.setToken(res.access_token);
    return res;
  }

  async devLogin(email: string): Promise<{ access_token: string; user: SupervisorProfile }> {
    const res = await this.request<{ access_token: string; user: SupervisorProfile }>(
      '/auth/dev-token',
      {
        method: 'POST',
        body: JSON.stringify({ email }),
      }
    );
    this.setToken(res.access_token);
    return res;
  }

  async getMe(): Promise<SupervisorProfile> {
    return this.request<SupervisorProfile>('/auth/me');
  }

  // Customer Voice Experience
  async getGreeting(name?: string, sessionId?: string): Promise<{ greeting: string; audio_base64?: string }> {
    const params = new URLSearchParams();
    if (name) params.append('name', name);
    if (sessionId) params.append('session_id', sessionId);
    const q = params.toString() ? `?${params.toString()}` : '';
    return this.request<{ greeting: string; audio_base64?: string }>(`/voice/greeting${q}`);
  }

  async createVoiceToken(customerName?: string, customerPhone?: string): Promise<VoiceTokenResponse> {
    return this.request<VoiceTokenResponse>('/voice/token', {
      method: 'POST',
      body: JSON.stringify({
        customer_name: customerName,
        customer_phone: customerPhone,
      }),
    });
  }

  async getVoiceSession(sessionId: string): Promise<CallSession> {
    return this.request<CallSession>(`/voice/sessions/${sessionId}`);
  }

  async sendSpeechTurn(sessionId: string, speech: string): Promise<{ reply: string; audio_base64?: string }> {
    return this.request<{ reply: string; audio_base64?: string }>(`/voice/sessions/${sessionId}/turn`, {
      method: 'POST',
      body: JSON.stringify({ speech }),
    });
  }

  async endVoiceSession(sessionId: string): Promise<CallSession> {
    return this.request<CallSession>(`/voice/sessions/${sessionId}/end`, {
      method: 'POST',
    });
  }

  async getSupervisorTurns(sessionId: string): Promise<Array<{ id: string; turn_id?: string; content: string; audio_base64?: string; mime_type?: string; is_human?: boolean; created_at?: string }>> {
    return this.request<Array<{ id: string; turn_id?: string; content: string; audio_base64?: string; mime_type?: string; is_human?: boolean; created_at?: string }>>(`/voice/sessions/${sessionId}/supervisor-turns`);
  }

  // Supervisor Calls Monitoring & Takeover
  async getActiveCalls(): Promise<CallSession[]> {
    return this.request<CallSession[]>('/calls/active');
  }

  async getCallHistory(page = 1, pageSize = 20): Promise<PaginatedResult<CallSession>> {
    return this.request<PaginatedResult<CallSession>>(`/calls/history?page=${page}&page_size=${pageSize}`);
  }

  async getTranscripts(sessionId: string): Promise<TranscriptTurn[]> {
    return this.request<TranscriptTurn[]>(`/calls/${sessionId}/transcripts`);
  }

  async takeoverCall(sessionId: string, notes?: string): Promise<{ token: string; room_name: string; livekit_url?: string }> {
    return this.request<{ token: string; room_name: string; livekit_url?: string }>(`/calls/${sessionId}/takeover`, {
      method: 'POST',
      body: JSON.stringify({ action: 'takeover_started', notes }),
    });
  }

  async getSupervisorToken(sessionId: string): Promise<{ token: string; room_name: string; livekit_url?: string }> {
    return this.request<{ token: string; room_name: string; livekit_url?: string }>(`/calls/${sessionId}/token`);
  }

  async handbackCall(sessionId: string, notes?: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/calls/${sessionId}/handback`, {
      method: 'POST',
      body: JSON.stringify({ action: 'handback_to_ai', notes }),
    });
  }

  async forceEndCall(sessionId: string): Promise<CallSession> {
    return this.request<CallSession>(`/calls/${sessionId}/end`, {
      method: 'POST',
    });
  }

  async sendSupervisorTurn(
    sessionId: string,
    speech: string,
    audioBase64?: string,
    mimeType?: string
  ): Promise<{ message: string; turn_id: string; content: string; audio_base64?: string; mime_type?: string; is_human?: boolean }> {
    return this.request<{ message: string; turn_id: string; content: string; audio_base64?: string; mime_type?: string; is_human?: boolean }>(
      `/calls/${sessionId}/supervisor-turn`,
      {
        method: 'POST',
        body: JSON.stringify({ speech, audio_base64: audioBase64, mime_type: mimeType }),
      }
    );
  }

  // Support Tickets
  async getTickets(status?: string, priority?: string, page = 1): Promise<PaginatedResult<SupportTicket>> {
    const params = new URLSearchParams({ page: String(page), page_size: '20' });
    if (status) params.append('status', status);
    if (priority) params.append('priority', priority);
    return this.request<PaginatedResult<SupportTicket>>(`/tickets?${params.toString()}`);
  }

  async updateTicket(ticketId: string, data: Partial<SupportTicket>): Promise<SupportTicket> {
    return this.request<SupportTicket>(`/tickets/${ticketId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // Knowledge base search
  async queryKnowledge(query: string): Promise<Array<{ chunk_id: string; document_title: string; content: string; score: number }>> {
    return this.request('/knowledge/query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }
}

export const api = new ApiClient();
