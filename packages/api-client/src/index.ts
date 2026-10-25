/**
 * Epoxa TypeScript API Client & Contract Types
 * Generated from FastAPI OpenAPI Schema (/api/v1)
 */

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string | null;
  instance?: string | null;
  request_id?: string | null;
  errors?: Array<{ loc: string[]; msg: string; type: string }> | null;
}

export interface CallStartRequest {
  participant_name?: string | null;
  phone?: string | null;
}

export interface CallStartResponse {
  session_id: string;
  room_name: string;
  token: string;
  livekit_url: string;
  identity: string;
}

export interface CallSessionResponse {
  id: string;
  organization_id: string;
  room_name: string;
  status: "active" | "escalated" | "completed" | "dropped" | "timeout" | "error";
  handoff_state: "ai" | "human_pending" | "human_active";
  participant_name?: string | null;
  participant_identity?: string | null;
  customer_id?: string | null;
  started_at: string;
  ended_at?: string | null;
  duration_seconds?: number | null;
  summary?: string | null;
  created_at: string;
}

export interface CallSessionListResponse {
  items: CallSessionResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface TranscriptTurnResponse {
  id: number;
  session_id: string;
  role: "user" | "agent" | "supervisor";
  content: string;
  sequence: number;
  spoken_at: string;
}

export interface CallTakeoverResponse {
  session_id: string;
  room_name: string;
  token: string;
  livekit_url: string;
  identity: string;
  handoff_state: string;
}

export interface AppointmentResponse {
  id: string;
  organization_id: string;
  customer_id: string;
  session_id?: string | null;
  scheduled_at: string;
  duration_minutes: number;
  confirmation_code: string;
  status: "confirmed" | "cancelled" | "completed" | "rescheduled" | "no_show";
  notes?: string | null;
  created_at: string;
}

export interface AppointmentListResponse {
  items: AppointmentResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface TicketResponse {
  id: string;
  number: number;
  organization_id: string;
  customer_id?: string | null;
  session_id?: string | null;
  category: "Complaint" | "Escalation" | "Billing" | "General" | "Technical";
  priority: "low" | "normal" | "high" | "urgent";
  description: string;
  status: "open" | "in_progress" | "resolved" | "closed";
  assigned_to?: string | null;
  created_at: string;
  resolved_at?: string | null;
}

export interface TicketListResponse {
  items: TicketResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface CustomerResponse {
  id: string;
  organization_id: string;
  name: string;
  phone_e164: string;
  email?: string | null;
  tier: "Basic" | "Standard" | "Premium" | "VIP";
  anonymized_at?: string | null;
  created_at: string;
}

export interface CustomerListResponse {
  items: CustomerResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProfileResponse {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  role: "owner" | "admin" | "supervisor";
  organization_id: string;
  organization_name: string;
}

export class EpoxaApiClient {
  private baseUrl: string;
  private tokenProvider?: () => Promise<string | null>;

  constructor(options: { baseUrl: string; tokenProvider?: () => Promise<string | null> }) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.tokenProvider = options.tokenProvider;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.tokenProvider) {
      const token = await this.tokenProvider();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }

    const res = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let problem: ProblemDetails;
      try {
        problem = await res.json();
      } catch {
        problem = {
          type: "about:blank",
          title: res.statusText,
          status: res.status,
          detail: await res.text(),
        };
      }
      throw problem;
    }

    return res.json() as Promise<T>;
  }

  // Calls
  public startCall(payload: CallStartRequest): Promise<CallStartResponse> {
    return this.request<CallStartResponse>("/api/v1/calls", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  public listCalls(params?: { status?: string; limit?: number; offset?: number }): Promise<CallSessionListResponse> {
    const q = new URLSearchParams();
    if (params?.status) q.append("status", params.status);
    if (params?.limit) q.append("limit", params.limit.toString());
    if (params?.offset) q.append("offset", params.offset.toString());
    return this.request<CallSessionListResponse>(`/api/v1/calls?${q.toString()}`);
  }

  public getCall(id: string): Promise<CallSessionResponse> {
    return this.request<CallSessionResponse>(`/api/v1/calls/${id}`);
  }

  public getTranscript(id: string): Promise<TranscriptTurnResponse[]> {
    return this.request<TranscriptTurnResponse[]>(`/api/v1/calls/${id}/transcript`);
  }

  public takeoverCall(id: string, notes?: string): Promise<CallTakeoverResponse> {
    return this.request<CallTakeoverResponse>(`/api/v1/calls/${id}/takeover`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    });
  }

  public handbackCall(id: string, notes?: string): Promise<{ status: string }> {
    return this.request<{ status: string }>(`/api/v1/calls/${id}/handback`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    });
  }

  public endCall(id: string, reason?: string): Promise<{ status: string }> {
    return this.request<{ status: string }>(`/api/v1/calls/${id}/end`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  // Me
  public getMe(): Promise<ProfileResponse> {
    return this.request<ProfileResponse>("/api/v1/me");
  }

  // Appointments
  public listAppointments(params?: { status?: string; limit?: number; offset?: number }): Promise<AppointmentListResponse> {
    const q = new URLSearchParams();
    if (params?.status) q.append("status", params.status);
    if (params?.limit) q.append("limit", params.limit.toString());
    if (params?.offset) q.append("offset", params.offset.toString());
    return this.request<AppointmentListResponse>(`/api/v1/appointments?${q.toString()}`);
  }

  // Tickets
  public listTickets(params?: { status?: string; category?: string; limit?: number; offset?: number }): Promise<TicketListResponse> {
    const q = new URLSearchParams();
    if (params?.status) q.append("status", params.status);
    if (params?.category) q.append("category", params.category);
    if (params?.limit) q.append("limit", params.limit.toString());
    if (params?.offset) q.append("offset", params.offset.toString());
    return this.request<TicketListResponse>(`/api/v1/tickets?${q.toString()}`);
  }

  public updateTicket(id: string, updates: { status?: string; priority?: string; assigned_to?: string }): Promise<TicketResponse> {
    return this.request<TicketResponse>(`/api/v1/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  }

  // Customers
  public listCustomers(params?: { limit?: number; offset?: number }): Promise<CustomerListResponse> {
    const q = new URLSearchParams();
    if (params?.limit) q.append("limit", params.limit.toString());
    if (params?.offset) q.append("offset", params.offset.toString());
    return this.request<CustomerListResponse>(`/api/v1/customers?${q.toString()}`);
  }

  public anonymizeCustomer(id: string): Promise<{ status: string }> {
    return this.request<{ status: string }>(`/api/v1/customers/${id}/anonymize`, {
      method: "POST",
    });
  }
}

export { EpoxaApiClient as VoiceAIApiClient, EpoxaApiClient as ApiClient };
