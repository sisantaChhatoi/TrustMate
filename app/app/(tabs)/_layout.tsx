import { Ionicons } from '@expo/vector-icons';
import * as Notifications from 'expo-notifications';
import { router, Tabs } from 'expo-router';
import { useEffect, useRef } from 'react';

import { colors } from '@/constants/design';
import { api } from '@/lib/api';
import { getToken } from '@/lib/auth';
import { setAlert } from '@/lib/alert-store';
import { registerForPushToken } from '@/lib/notifications';

export default function TabLayout() {
  const notifListener = useRef<Notifications.EventSubscription>();
  const responseListener = useRef<Notifications.EventSubscription>();

  useEffect(() => {
    getToken().then((token) => {
      if (!token) router.replace('/onboarding');
    });

    registerForPushToken()
      .then((token) => (token ? api.registerPushToken(token) : null))
      .catch(() => null);

    // Foreground: store alert data so the Alerts tab updates immediately.
    notifListener.current = Notifications.addNotificationReceivedListener((notification) => {
      const data = notification.request.content.data as Record<string, unknown>;
      if (data?.type === 'scam_alert') {
        setAlert({
          scam: true,
          confidence: (data.confidence as number) ?? 1,
          reason: (data.reason as string) ?? '',
          red_flags: (data.red_flags as string[]) ?? [],
          caller: (data.caller as string | null) ?? null,
          received_at: new Date().toISOString(),
        });
      }
    });

    // Tap: navigate to the Alerts tab.
    responseListener.current = Notifications.addNotificationResponseReceivedListener((response) => {
      const data = response.notification.request.content.data as Record<string, unknown>;
      if (data?.type === 'scam_alert') {
        router.navigate('/(tabs)/alerts');
      }
    });

    return () => {
      notifListener.current?.remove();
      responseListener.current?.remove();
    };
  }, []);

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors.faint,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
      }}>
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ color, size, focused }) => (
            <Ionicons name={focused ? 'home' : 'home-outline'} size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="alerts"
        options={{
          title: 'Alerts',
          tabBarIcon: ({ color, size, focused }) => (
            <Ionicons name={focused ? 'warning' : 'warning-outline'} size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="protection"
        options={{
          title: 'Protection',
          tabBarIcon: ({ color, size, focused }) => (
            <Ionicons
              name={focused ? 'shield-checkmark' : 'shield-checkmark-outline'}
              size={size}
              color={color}
            />
          ),
        }}
      />
    </Tabs>
  );
}
