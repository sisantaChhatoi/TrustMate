import { API_URL } from '@/constants/config';
import { getToken } from './auth';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type Options = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  auth?: boolean;
};

async function request<T>(path: string, opts: Options = {}): Promise<T> {
  const { method = 'GET', body, auth = false } = opts;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };

  if (auth) {
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection.");
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const detail = (data && (data.detail ?? data.message)) || `Request failed (${res.status})`;
    throw new ApiError(res.status, typeof detail === 'string' ? detail : 'Request failed');
  }
  return data as T;
}

export type Languages = { primary: string; secondary: string | null; tertiary: string | null };

export type UserPublic = {
  user_id: string;
  name: string;
  phone_no: string;
  state: string;
  city: string;
  pin: string;
  languages: Languages;
  age: number;
  created_at: string;
};

export type AuthResponse = { access_token: string; token_type: string; user: UserPublic };

export type SignupPayload = {
  name: string;
  phone_no: string;
  password: string;
  state: string;
  city: string;
  pin: string;
  languages: Languages;
  age: number;
};

export type ChatMessage = { role: 'user' | 'agent'; message: string; time: string };
export type ChatSummary = { chat_id: string; title: string };
export type Chat = { chat_id: string; user_id: string; title: string; messages: ChatMessage[] };

export type Notification = {
  confidence: number;
  reason: string;
  red_flags: string[];
  sent_at: string;
};

export type CallStats = {
  scanned: number;
  threats_blocked: number;
  marked_safe: number;
  last_scanned_at: string | null;
};

export type LinkCheckResult = {
  url: string;
  verdict: 'safe' | 'unsafe';
  google_safe_browsing: { safe: boolean; threat: string | null };
  virustotal: { safe: boolean | null; malicious: number; suspicious: number; note: string | null };
};

export type CallSummary = {
  started_at: string;
  ended_at: string | null;
  flagged: boolean;
};

export type FraudRing = {
  ring_id: string;
  size: number;
  incident_count: number;
  mule_accounts: string[];
  phone_numbers: string[];
  victim_regions: string[];
  scam_types: string[];
  total_amount_demanded: number;
  total_amount_lost: number;
};

export type FraudHotspot = {
  region: string;
  state: string;
  lat: number;
  lon: number;
  incident_count: number;
  total_amount_demanded: number;
  total_amount_lost: number;
  scam_types: string[];
  risk_level: 'low' | 'medium' | 'high';
};

export type HighRiskAccount = {
  node: string;
  type: string;
  value: string;
  incident_count: number;
  risk_level: 'low' | 'medium' | 'high';
  linked_entities: { node: string; type: string; value: string }[];
  ring_id: string | null;
};

export type IntelligenceRings = { generated_at: string; rings: FraudRing[] };
export type IntelligenceHotspots = {
  generated_at: string;
  hotspots: FraudHotspot[];
  deployment_strategy: Record<string, unknown>;
};
export type IntelligenceAccounts = { generated_at: string; accounts: HighRiskAccount[] };

export const api = {
  signup: (payload: SignupPayload) =>
    request<AuthResponse>('/auth/signup', { method: 'POST', body: payload }),
  login: (phone_no: string, password: string) =>
    request<AuthResponse>('/auth/login', { method: 'POST', body: { phone_no, password } }),
  me: () => request<UserPublic>('/auth/me', { auth: true }),
  registerPushToken: (push_token: string) =>
    request<null>('/auth/push-token', { method: 'POST', body: { push_token }, auth: true }),
  testNotify: () =>
    request<{ status: string; resolved_phone: string; test_target: string }>('/test/notify', {
      method: 'POST',
      auth: true,
    }),
  createChat: () => request<Chat>('/chatbot/chats', { method: 'POST', body: {}, auth: true }),
  listChats: () => request<ChatSummary[]>('/chatbot/chats', { auth: true }),
  getChat: (id: string) => request<Chat>(`/chatbot/chats/${id}`, { auth: true }),
  getNotifications: () => request<Notification[]>('/notifications', { auth: true }),
  getCallStats: () => request<CallStats>('/calls/stats', { auth: true }),
  getRecentCalls: (limit: number) =>
    request<CallSummary[]>(`/calls?limit=${limit}`, { auth: true }),
  checkLink: (url: string) =>
    request<LinkCheckResult>('/link-check', { method: 'POST', body: { url }, auth: true }),
  getRings: () => request<IntelligenceRings>('/intelligence/rings', { auth: true }),
  getHotspots: () => request<IntelligenceHotspots>('/intelligence/hotspots', { auth: true }),
  getHighRiskAccounts: (minRisk = 'medium') =>
    request<IntelligenceAccounts>(`/intelligence/high-risk-accounts?min_risk=${minRisk}`, {
      auth: true,
    }),
};
