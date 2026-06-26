import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { View } from 'react-native';

import { AppText } from '@/components/ui/app-text';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { FeatureRow } from '@/components/ui/feature-row';
import { IconBadge } from '@/components/ui/icon-badge';
import { Screen } from '@/components/ui/screen';
import { SectionHeader } from '@/components/ui/section-header';
import { colors, radius, space } from '@/constants/design';

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
      'Every alert explains the red flags — OTP requests, urgency, account-block threats — in plain language.',
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
  { title: 'Add the guard to your call', description: 'A tap brings the agent into an active call.' },
  { title: 'It listens and analyzes', description: 'Speech is transcribed and checked for scam tactics live.' },
  { title: 'You get an explained warning', description: 'A push alert names the threat and the red flags.' },
];

export default function LandingScreen() {
  return (
    <Screen>
      <BrandBar />
      <Hero />
      <Capabilities />
      <HowItWorks />
      <Footer />
    </Screen>
  );
}

function BrandBar() {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
      <IconBadge name="shield-checkmark" tone="brand" size="sm" />
      <AppText variant="heading">CallGuard</AppText>
    </View>
  );
}

function Hero() {
  return (
    <LinearGradient
      colors={[colors.brand, colors.brandDark]}
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
        CallGuard puts an AI agent on the line that spots fraud as it happens — and warns
        you in seconds, in words you understand.
      </AppText>

      <Button label="Activate protection" icon="shield-checkmark" variant="secondary" />
    </LinearGradient>
  );
}

function Capabilities() {
  return (
    <View style={{ gap: space.lg }}>
      <SectionHeader
        eyebrow="What it does"
        title="Protection that explains itself"
        description="Not just a “scam” label — the reasoning behind every alert."
      />
      <Card>
        <View style={{ gap: space.lg }}>
          {CAPABILITIES.map((c, i) => (
            <View key={c.title} style={{ gap: space.lg }}>
              {i > 0 ? (
                <View style={{ height: 1, backgroundColor: colors.border }} />
              ) : null}
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
            <View key={s.title} style={{ flexDirection: 'row', alignItems: 'flex-start', gap: space.md }}>
              <View
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: radius.pill,
                  backgroundColor: colors.brandTint,
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                <AppText variant="bodyStrong" color={colors.brand}>
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

function Footer() {
  return (
    <Card>
      <View style={{ gap: space.lg, alignItems: 'flex-start' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
          <IconBadge name="heart-outline" tone="brand" size="md" />
          <View style={{ flex: 1 }}>
            <AppText variant="subtitle">Built to protect the people you love</AppText>
            <AppText variant="caption">
              Set it up once on a parent’s phone — they stay covered automatically.
            </AppText>
          </View>
        </View>
        <Button label="Activate protection" icon="arrow-forward" full />
      </View>
    </Card>
  );
}
