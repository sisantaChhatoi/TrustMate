const _listeners = new Set<() => void>();

export function notifyAlertArrived(): void {
  _listeners.forEach((fn) => fn());
}

export function subscribeAlert(fn: () => void): () => void {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}
