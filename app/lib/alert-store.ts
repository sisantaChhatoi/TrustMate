export type ScamAlert = {
  scam: boolean;
  confidence: number;
  reason: string;
  red_flags: string[];
  caller: string | null;
  received_at: string;
};

let _lastAlert: ScamAlert | null = null;
const _listeners = new Set<() => void>();

export function setAlert(alert: ScamAlert): void {
  _lastAlert = alert;
  _listeners.forEach((fn) => fn());
}

export function getAlert(): ScamAlert | null {
  return _lastAlert;
}

export function subscribeAlert(fn: () => void): () => void {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}
