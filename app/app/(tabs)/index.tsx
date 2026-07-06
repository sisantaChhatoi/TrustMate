import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useState } from 'react';
import { Alert, View } from 'react-native';

import { AppText } from '@/components/ui/app-text';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { FeatureRow } from '@/components/ui/feature-row';
import { IconBadge } from '@/components/ui/icon-badge';
import { Screen } from '@/components/ui/screen';
import { SectionHeader } from '@/components/ui/section-header';
import { TopBar } from '@/components/ui/top-bar';
import { colors, radius, space } from '@/constants/design';
import { flags } from '@/constants/flags';
import { api, ApiError } from '@/lib/api';

const CAPABILITIES = [
  {
    icon: 'shield-checkmark-outline' as const,
    title: 'Real-time protection',
    description:
      'An AI agent listens to your live call and flags scam patterns the moment they appear.',
  },
  {
    icon: 'notifications-outline' as const,
    title: 'Instant alerts',
    description:
      'A clear warning reaches your phone even when the app is closed or in your pocket.',
  },
  {
    icon: 'document-text-outline' as const,
    title: 'Tells you why',
    description:
      'Every alert explains the red flags - OTP requests, urgency, account-block threats - in plain language.',
  },
  {
    icon: 'language-outline' as const,
    title: 'Understands your language',
    description: 'Detects scams across English and major Indian languages, accent and all.',
  },
  {
    icon: 'call-outline' as const,
    title: 'Caller insight',
    description: 'Surfaces the flagged number so you can block and report it in one tap.',
  },
  {
    icon: 'lock-closed-outline' as const,
    title: 'Private by design',
    description: 'The agent listens only to spot scams. Nothing else leaves your call.',
  },
];

const STEPS = [
  {
    title: 'Add the guard to your call',
    description: 'A tap brings the agent into an active call.',
  },
  {
    title: 'It listens and analyzes',
    description: 'Speech is transcribed and checked for scam tactics live.',
  },
  {
    title: 'You get an explained warning',
    description: 'A push alert names the threat and the red flags.',
  },
];

export default function LandingScreen() {
  return (
    <Screen>
      <TopBar />
      <Hero />
      <Capabilities />
      <HowItWorks />
      {flags.showTestNotify && <TestNotify />}
    </Screen>
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

function Hero() {
  return (
    <LinearGradient
      colors={[colors.brand, colors.teal]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={{ borderRadius: radius.xl, padding: space.xxl, gap: space.lg }}>
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: space.sm,
          alignSelf: 'flex-start',
          backgroundColor: 'rgba(255,255,255,0.16)',
          paddingHorizontal: space.md,
          paddingVertical: 6,
          borderRadius: radius.pill,
        }}>
        <Ionicons name="radio-outline" size={14} color={colors.white} />
        <AppText variant="label" color="rgba(255,255,255,0.95)">
          Live protection
        </AppText>
      </View>

      <AppText variant="display" color={colors.white}>
        Scam calls, caught before you fall for them.
      </AppText>
      <AppText variant="body" color="rgba(255,255,255,0.88)">
        An AI agent joins the line, spots fraud as it happens, and warns you in seconds - in words
        you understand.
      </AppText>
    </LinearGradient>
  );
}

function Capabilities() {
  return (
    <View style={{ gap: space.lg }}>
      <SectionHeader eyebrow="What it does" title="Protection that explains itself" />
      <Card>
        <View style={{ gap: space.lg }}>
          {CAPABILITIES.map((c, i) => (
            <View key={c.title} style={{ gap: space.lg }}>
              {i > 0 ? <View style={{ height: 1, backgroundColor: colors.border }} /> : null}
              <FeatureRow icon={c.icon} title={c.title} description={c.description} />
            </View>
          ))}
        </View>
      </Card>
    </View>
  );
}

function HowItWorks() {
  return (
    <View style={{ gap: space.lg }}>
      <SectionHeader eyebrow="How it works" title="Three steps to safety" />
      <Card>
        <View style={{ gap: space.xl }}>
          {STEPS.map((s, i) => (
            <View
              key={s.title}
              style={{ flexDirection: 'row', alignItems: 'flex-start', gap: space.md }}>
              <View
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: radius.pill,
                  backgroundColor: colors.tealTint,
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                <AppText variant="bodyStrong" color={colors.teal}>
                  {i + 1}
                </AppText>
              </View>
              <View style={{ flex: 1, gap: 2, paddingTop: 2 }}>
                <AppText variant="subtitle">{s.title}</AppText>
                <AppText variant="caption">{s.description}</AppText>
              </View>
            </View>
          ))}
        </View>
      </Card>
    </View>
  );
}
