import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Alert, Linking, Pressable, View } from 'react-native';

import { AppText } from '@/components/ui/app-text';
import { Button } from '@/components/ui/button';
import { CallList } from '@/components/ui/call-list';
import { Card } from '@/components/ui/card';
import { IconBadge } from '@/components/ui/icon-badge';
import { Screen } from '@/components/ui/screen';
import { SectionHeader } from '@/components/ui/section-header';
import { StatTiles } from '@/components/ui/stat-tiles';
import { TopBar } from '@/components/ui/top-bar';
import { AGENT_PHONE_NO } from '@/constants/app';
import { colors, radius, space } from '@/constants/design';
import { flags } from '@/constants/flags';
import { api, ApiError, type CallStats, type CallSummary } from '@/lib/api';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

const DISPLAY_NO = AGENT_PHONE_NO.replace(/(\+\d)(\d{3})(\d{3})(\d{4})/, '$1 $2 $3 $4');

const STEPS = [
  'On a suspicious call, tap Add call',
  `Dial CallGuard — ${DISPLAY_NO}`,
  'Tap Merge calls — the guard joins and listens',
  'Keep talking; an alert lands the moment it hears a scam',
];

export default function LandingScreen() {
  const [stats, setStats] = useState<CallStats | null>(null);
  const [recent, setRecent] = useState<CallSummary[]>([]);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([api.getCallStats(), api.getRecentCalls(5)]);
      setStats(s);
      setRecent(r);
    } catch {
      // keep prior state; the empty state renders until data arrives
    } finally {
      setLoaded(true);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  const hasActivity = (stats?.scanned ?? 0) > 0;

  return (
    <Screen>
      <TopBar />
      {!loaded ? (
        <View style={{ paddingVertical: space.huge, alignItems: 'center' }}>
          <ActivityIndicator color={colors.brand} />
        </View>
      ) : hasActivity ? (
        <Dashboard stats={stats} recent={recent} />
      ) : (
        <GetStarted />
      )}
      <LinkCheckerCard />
      <ReportFooter />
      {flags.showTestNotify && <TestNotify />}
    </Screen>
  );
}

function GetStarted() {
  return (
    <View style={{ gap: space.md }}>
      <SectionHeader eyebrow="Get started" icon="shield-checkmark-outline" />
      <Card>
        <View style={{ gap: space.lg }}>
          <Ionicons name="call" size={30} color={colors.brandDark} />
          <View style={{ gap: 4 }}>
            <AppText variant="heading">Add CallGuard to your next call</AppText>
            <AppText variant="body">
              Dial the guard into a suspicious call and it listens for scams in real time.
            </AppText>
          </View>
          <Pressable
            onPress={() => Linking.openURL(`tel:${AGENT_PHONE_NO}`)}
            style={({ pressed }) => ({
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: space.sm,
              paddingVertical: space.md,
              paddingHorizontal: space.lg,
              borderRadius: radius.md,
              backgroundColor: colors.brand,
              opacity: pressed ? 0.85 : 1,
            })}>
            <AppText variant="title" color={colors.white} style={{ fontSize: 20 }}>
              {DISPLAY_NO}
            </AppText>
            <Ionicons name="call" size={18} color={colors.white} />
          </Pressable>
          <View style={{ gap: space.md }}>
            {STEPS.map((s, i) => (
              <View key={s} style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
                <View
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: radius.pill,
                    backgroundColor: colors.brandTint,
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                  <AppText variant="caption" color={colors.brandDark}>
                    {i + 1}
                  </AppText>
                </View>
                <AppText variant="caption" color={colors.body} style={{ flex: 1 }}>
                  {s}
                </AppText>
              </View>
            ))}
          </View>
        </View>
      </Card>
    </View>
  );
}

function Dashboard({ stats, recent }: { stats: CallStats | null; recent: CallSummary[] }) {
  return (
    <>
      <View style={{ gap: space.md }}>
        <SectionHeader eyebrow="Your activity" icon="stats-chart-outline" />
        <StatTiles stats={stats} />
      </View>
      {recent.length > 0 ? (
        <View style={{ gap: space.md }}>
          <SectionHeader eyebrow="Recent activity" icon="time-outline" />
          <Card>
            <View style={{ gap: space.lg }}>
              <CallList calls={recent} />
              <Pressable
                onPress={() => router.navigate('/(tabs)/protection')}
                style={({ pressed }) => ({
                  flexDirection: 'row',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: space.xs,
                  opacity: pressed ? 0.6 : 1,
                })}>
                <AppText variant="bodyStrong" color={colors.brandDark}>
                  View more
                </AppText>
                <Ionicons name="chevron-forward" size={16} color={colors.brandDark} />
              </Pressable>
            </View>
          </Card>
        </View>
      ) : null}
    </>
  );
}

function LinkCheckerCard() {
  return (
    <Card>
      <View style={{ gap: space.md }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
          <IconBadge name="link-outline" tone="brand" size="sm" />
          <AppText variant="subtitle">Link checker</AppText>
        </View>
        <AppText variant="caption">
          Got a suspicious link in a message or email? Check it instantly against Google Safe
          Browsing and VirusTotal.
        </AppText>
        <Button
          label="Check a link"
          icon="shield-checkmark-outline"
          onPress={() => router.navigate('/link-checker')}
          full
        />
      </View>
    </Card>
  );
}

function ReportFooter() {
  return (
    <View style={{ gap: space.md }}>
      <SectionHeader eyebrow="Report a scam" icon="megaphone-outline" />
      <Card variant="flat" tint="br">
        <View style={{ gap: space.md }}>
          <AppText variant="caption">
            Spotted something? Report it to the national cybercrime helpline.
          </AppText>
          <View style={{ flexDirection: 'row', gap: space.md }}>
            <ReportChip
              icon="call-outline"
              label="Call 1930"
              onPress={() => Linking.openURL('tel:1930')}
            />
            <ReportChip
              icon="globe-outline"
              label="cybercrime.gov.in"
              onPress={() => Linking.openURL('https://cybercrime.gov.in')}
            />
          </View>
        </View>
      </Card>
    </View>
  );
}

function ReportChip({
  icon,
  label,
  onPress,
}: {
  icon: IconName;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => ({
        flexDirection: 'row',
        alignItems: 'center',
        gap: space.sm,
        paddingVertical: space.xs,
        opacity: pressed ? 0.6 : 1,
      })}>
      <Ionicons name={icon} size={16} color={colors.muted} />
      <AppText variant="bodyStrong" color={colors.body}>
        {label}
      </AppText>
    </Pressable>
  );
}

function TestNotify() {
  const [sending, setSending] = useState(false);

  const onPress = async () => {
    setSending(true);
    try {
      const res = await api.testNotify();
      Alert.alert('Notification sent', `A test alert was pushed for ${res.test_target}.`);
    } catch (e) {
      Alert.alert('Could not send', e instanceof ApiError ? e.message : 'Something went wrong.');
    } finally {
      setSending(false);
    }
  };

  return (
    <Card>
      <View style={{ gap: space.md, alignItems: 'flex-start' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
          <IconBadge name="notifications-outline" tone="brand" size="sm" />
          <AppText variant="subtitle">Test notification</AppText>
        </View>
        <AppText variant="caption">Sends a sample scam alert to this device.</AppText>
        <Button
          label={sending ? 'Sending...' : 'Send test notification'}
          icon="notifications-outline"
          onPress={onPress}
          full
        />
      </View>
    </Card>
  );
}
