// A real phone can't reach `localhost` — use your machine's LAN IP or an ngrok URL.
export const API_URL =
  process.env.EXPO_PUBLIC_API_URL ?? 'http://192.168.1.37:8000';
