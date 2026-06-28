import { api, ApiError } from './api';
import { getToken } from './auth';

export type StartRoute = '/(tabs)' | '/login' | '/signup';

export async function resolveStartRoute(): Promise<StartRoute> {
  const token = await getToken();
  if (!token) return '/signup';
  try {
    await api.me();
    return '/(tabs)';
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return '/login';
    // Can't verify (server down etc) — fall back to login so they can retry.
    return '/login';
  }
}
