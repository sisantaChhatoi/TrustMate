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

export type Chat = { id: string; user_id: string; created_at: string };
export type ChatMessage = { role: 'user' | 'assistant'; content: string; created_at?: string };
export type ChatDetail = Chat & { messages: ChatMessage[] };

export type Notification = {
  confidence: number;
  reason: string;
  red_flags: string[];
  sent_at: string;
};

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
  createChat: () => request<Chat>('/chatbot/chats', { method: 'POST', auth: true }),
  listChats: () => request<Chat[]>('/chatbot/chats', { auth: true }),
  getChat: (id: string) => request<ChatDetail>(`/chatbot/chats/${id}`, { auth: true }),
  getNotifications: () => request<Notification[]>('/notifications', { auth: true }),
};
