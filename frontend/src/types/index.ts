export type CallStatus =
  | 'initiating'
  | 'active'
  | 'escalated'
  | 'supervisor_takeover'
  | 'completed'
  | 'failed';

export type HandoffState =
  | 'none'
  | 'requested'
  | 'accepted'
  | 'rejected'
  | 'returned_to_ai';

export interface CallSummary {
  id: string;
  call_session_id: string;
  summary: string;
  primary_intent?: string;
  detected_sentiment?: 'positive' | 'neutral' | 'negative' | 'frustrated';
  follow_up_required: boolean;
  created_at: string;
}

export interface CallSession {
  id: string;
  organization_id: string;
  business_id?: string;
  customer_id?: string;
  room_name: string;
  status: CallStatus;
  handoff_state: HandoffState;
  started_at?: string;
  ended_at?: string;
  duration_seconds?: number;
  termination_reason?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  summary?: CallSummary;
}

export interface TranscriptTurn {
  id: string;
  call_session_id: string;
  speaker: 'customer' | 'ai_agent' | 'supervisor';
  content?: string;
  is_purged: boolean;
  purged_at?: string;
  created_at: string;
}

export interface SupportTicket {
  id: string;
  organization_id: string;
  business_id?: string;
  customer_id?: string;
  call_session_id?: string;
  assigned_supervisor_id?: string;
  ticket_number: string;
  title: string;
  description: string;
  category: 'general' | 'technical' | 'billing' | 'escalation';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'open' | 'in_progress' | 'pending_customer' | 'resolved' | 'closed';
  resolved_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Customer {
  id: string;
  organization_id: string;
  business_id?: string;
  display_name?: string;
  phone_number?: string;
  email?: string;
  company_name?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface SupervisorProfile {
  user_id: string;
  email: string;
  full_name: string;
  organization_id: string;
  role: string;
}

export interface VoiceTokenResponse {
  token: string;
  room_name: string;
  session_id: string;
  livekit_url: string;
  expires_in_seconds: number;
  created_at?: string;
}

export interface HealthStatus {
  status: string;
  version: string;
  environment: string;
  database: string;
  livekit: string;
  deepgram: string;
  groq: string;
  timestamp: string;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
