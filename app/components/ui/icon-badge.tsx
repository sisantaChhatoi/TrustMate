import { Ionicons } from '@expo/vector-icons';
import { View } from 'react-native';

import { colors, radius } from '@/constants/design';

type IconName = React.ComponentProps<typeof Ionicons>['name'];
type Tone = 'brand' | 'neutral' | 'danger' | 'success';
type Size = 'sm' | 'md' | 'lg';

const TONES: Record<Tone, { bg: string; fg: string }> = {
  brand: { bg: colors.brandTint, fg: colors.brand },
  neutral: { bg: colors.surfaceAlt, fg: colors.body },
  danger: { bg: colors.dangerTint, fg: colors.danger },
  success: { bg: colors.successTint, fg: colors.success },
};

const SIZES: Record<Size, { box: number; icon: number; r: number }> = {
  sm: { box: 36, icon: 18, r: radius.sm },
  md: { box: 44, icon: 20, r: radius.md },
  lg: { box: 56, icon: 26, r: radius.lg },
};

/** A rounded, tinted container for a single icon. Keeps icon styling uniform. */
export function IconBadge({
  name,
  tone = 'brand',
  size = 'md',
}: {
  name: IconName;
  tone?: Tone;
  size?: Size;
}) {
  const t = TONES[tone];
  const s = SIZES[size];
  return (
    <View
      style={{
        width: s.box,
        height: s.box,
        borderRadius: s.r,
        backgroundColor: t.bg,
        alignItems: 'center',
        justifyContent: 'center',
      }}>
      <Ionicons name={name} size={s.icon} color={t.fg} />
    </View>
  );
}
