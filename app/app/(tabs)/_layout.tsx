import { Ionicons } from '@expo/vector-icons';
import Constants, { ExecutionEnvironment } from 'expo-constants';
import { router, Tabs } from 'expo-router';
import { useEffect, useRef } from 'react';

import { colors } from '@/constants/design';
import { api } from '@/lib/api';
import { getToken } from '@/lib/auth';
import { notifyAlertArrived } from '@/lib/alert-store';

const isExpoGo = Constants.executionEnvironment === ExecutionEnvironment.StoreClient;

export default function TabLayout() {
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    getToken().then((token) => {
      if (!token) router.replace('/onboarding');
    });

    if (!isExpoGo) {
      // require (not import): a static import is hoisted and would load these in Expo Go,
      // whose SDK 53+ crashes on their load-time push side effects.
      /* eslint-disable @typescript-eslint/no-require-imports */
      const { registerForPushToken } =
        require('@/lib/notifications') as typeof import('@/lib/notifications');
      const Notifications = require('expo-notifications') as typeof import('expo-notifications');
      /* eslint-enable @typescript-eslint/no-require-imports */

      registerForPushToken()
        .then((token) => (token ? api.registerPushToken(token) : null))
        .catch(() => null);

      const notifListener = Notifications.addNotificationReceivedListener((notification) => {
        const data = notification.request.content.data as Record<string, unknown>;
        if (data?.type === 'scam_alert') {
          notifyAlertArrived();
        }
      });

      const responseListener = Notifications.addNotificationResponseReceivedListener((response) => {
        const data = response.notification.request.content.data as Record<string, unknown>;
        if (data?.type === 'scam_alert') {
          // @ts-ignore
          router.navigate('/(tabs)/alerts');
        }
      });

      cleanupRef.current = () => {
        notifListener.remove();
        responseListener.remove();
      };
    }

    return () => cleanupRef.current?.();
  }, []);

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors.faint,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
        tabBarShowLabel: false,
      }}>
      <Tabs.Screen
        name="index"
        options={{
          tabBarIcon: ({ color, size, focused }) => (
            <Ionicons name={focused ? 'home' : 'home-outline'} size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          tabBarIcon: ({ color, size, focused }) => (
            <Ionicons
              name={focused ? 'chatbubble-ellipses' : 'chatbubble-ellipses-outline'}
              size={size}
              color={color}
            />
          ),
        }}
      />
      <Tabs.Screen
        name="protection"
        options={{
          tabBarIcon: ({ color, size, focused }) => (
            <Ionicons
              name={focused ? 'shield-checkmark' : 'shield-checkmark-outline'}
              size={size}
              color={color}
            />
          ),
        }}
      />
      <Tabs.Screen name="alerts" options={{ href: null }} />
    </Tabs>
  );
}
