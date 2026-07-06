import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';

import { AppText } from '@/components/ui/app-text';
import { Card } from '@/components/ui/card';
import { Screen } from '@/components/ui/screen';
import { SectionHeader } from '@/components/ui/section-header';
import { colors, radius, space } from '@/constants/design';
import { subscribeAlert } from '@/lib/alert-store';
import { api, ApiError, type Notification } from '@/lib/api';

export default function AlertsScreen() {
  const [items, setItems] = useState<Notification[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      setItems(await api.getNotifications());
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not load alerts.');
    } finally {
      setLoaded(true);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  useEffect(() => subscribeAlert(load), [load]);

  return (
    <Screen>
      <SectionHeader eyebrow="History" title="Scam Alerts" />
      {error && loaded && items.length === 0 ? (
        <LoadError message={error} />
      ) : items.length > 0 ? (
        <View style={{ gap: space.md }}>
          {items.map((n) => (
            <AlertCard key={n.sent_at} alert={n} />
          ))}
        </View>
      ) : loaded ? (
        <NoAlerts />
      ) : null}
    </Screen>
  );
}

function AlertCard({ alert }: { alert: Notification }) {
  const pct = Math.round(alert.confidence * 100);

  return (
    <View style={{ gap: space.md }}>
      <View
        style={{
          backgroundColor: colors.dangerTint,
          borderColor: colors.dangerBorder,
          borderWidth: 1,
          borderRadius: radius.lg,
          padding: space.xxl,
          gap: space.lg,
        }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
          <View
            style={{
              width: 48,
              height: 48,
              borderRadius: radius.md,
              backgroundColor: colors.danger,
              alignItems: 'center',
              justifyContent: 'center',
            }}>
            <Ionicons name="warning" size={26} color={colors.white} />
          </View>
          <View style={{ flex: 1 }}>
            <AppText variant="heading" color={colors.danger}>
              Scam detected
            </AppText>
            <AppText variant="caption">
              Confidence {pct}% · {new Date(alert.sent_at).toLocaleString()}
            </AppText>
          </View>
        </View>
        <AppText variant="body">{alert.reason}</AppText>
      </View>

      {alert.red_flags.length > 0 && (
        <Card style={{ padding: space.lg, gap: space.md }}>
          <AppText variant="label">Red flags</AppText>
          {alert.red_flags.map((flag) => (
            <View key={flag} style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
              <Ionicons name="alert-circle" size={14} color={colors.danger} />
              <AppText variant="body">{flag}</AppText>
            </View>
          ))}
        </Card>
      )}
    </View>
  );
}

function LoadError({ message }: { message: string }) {
  return (
    <View style={{ alignItems: 'center', paddingVertical: space.huge, gap: space.lg }}>
      <Ionicons name="cloud-offline-outline" size={52} color={colors.faint} />
      <AppText variant="subtitle" color={colors.muted}>
        {message}
      </AppText>
    </View>
  );
}

function NoAlerts() {
  return (
    <View style={{ alignItems: 'center', paddingVertical: space.huge, gap: space.lg }}>
      <Ionicons name="shield-checkmark-outline" size={52} color={colors.faint} />
      <AppText variant="subtitle" color={colors.muted}>
        No alerts yet
      </AppText>
      <AppText variant="caption" style={{ textAlign: 'center' }}>
        Scam warnings appear here when the agent detects suspicious activity on your calls.
      </AppText>
    </View>
  );
}
