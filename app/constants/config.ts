// A real phone can't reach `localhost` — use your machine's LAN IP or an ngrok URL.
// EXPO_PUBLIC_API_URL is set in eas.json for APK builds.
// For Expo Go dev mode, run: npx localtunnel --port 8000
// then paste the https URL here as the fallback.
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://192.168.1.4:8000';
