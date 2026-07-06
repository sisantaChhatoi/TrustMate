import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { View } from 'react-native';

import { AppText } from '@/components/ui/app-text';
import { Card } from '@/components/ui/card';
import { IconBadge } from '@/components/ui/icon-badge';
import { Screen } from '@/components/ui/screen';
import { TopBar } from '@/components/ui/top-bar';
import { colors, radius, space } from '@/constants/design';

const STATS = [
  { icon: 'call-outline' as const, value: '12', label: 'Calls screened' },
  { icon: 'shield-outline' as const, value: '3', label: 'Threats blocked' },
  { icon: 'checkmark-done-outline' as const, value: '9', label: 'Marked safe' },
];

export default function ProtectionScreen() {
  return (
    <Screen>
      <TopBar title="Protection" />
      <StatusHero />
      <Stats />
    </Screen>
  );
}

function StatusHero() {
  return (
    <LinearGradient
      colors={[colors.teal, colors.brand]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={{ borderRadius: radius.xl, padding: space.xxl, gap: space.lg }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
        <View
          style={{
            width: 52,
            height: 52,
            borderRadius: radius.lg,
            backgroundColor: 'rgba(255,255,255,0.16)',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
          <Ionicons name="shield-checkmark" size={28} color={colors.white} />
        </View>
        <View style={{ flex: 1 }}>
          <AppText variant="title" color={colors.white}>
            Protection active
          </AppText>
          <AppText variant="caption" color="rgba(255,255,255,0.85)">
            Listening for scam patterns on your calls
          </AppText>
        </View>
      </View>

      <View style={{ flexDirection: 'row', gap: space.xl }}>
        <HeroMeta icon="time-outline" text="Since 6:02 PM" />
        <HeroMeta icon="call-outline" text="1 call connected" />
      </View>
    </LinearGradient>
  );
}

function HeroMeta({
  icon,
  text,
}: {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  text: string;
}) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
      <Ionicons name={icon} size={14} color="rgba(255,255,255,0.85)" />
      <AppText variant="caption" color="rgba(255,255,255,0.9)">
        {text}
      </AppText>
    </View>
  );
}

function Stats() {
  return (
    <View style={{ flexDirection: 'row', gap: space.md }}>
      {STATS.map((s) => (
        <Card key={s.label} style={{ flex: 1, padding: space.lg, gap: space.sm }}>
          <IconBadge name={s.icon} tone="brand" size="sm" />
          <AppText variant="title">{s.value}</AppText>
          <AppText variant="caption">{s.label}</AppText>
        </Card>
      ))}
    </View>
  );
}
