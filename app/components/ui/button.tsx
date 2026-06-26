import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleProp, View, ViewStyle } from 'react-native';

import { colors, radius, space } from '@/constants/design';
import { AppText } from './app-text';

type IconName = React.ComponentProps<typeof Ionicons>['name'];
type Variant = 'primary' | 'secondary' | 'ghost';

const STYLES: Record<Variant, { bg: string; border: string; fg: string }> = {
  primary: { bg: colors.brand, border: colors.brand, fg: colors.white },
  secondary: { bg: colors.surface, border: colors.borderStrong, fg: colors.ink },
  ghost: { bg: 'transparent', border: 'transparent', fg: colors.brand },
};

export function Button({
  label,
  onPress,
  variant = 'primary',
  icon,
  full,
  style,
}: {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  icon?: IconName;
  full?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const v = STYLES[variant];
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        {
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'center',
          gap: space.sm,
          paddingVertical: 14,
          paddingHorizontal: space.xl,
          borderRadius: radius.md,
          backgroundColor: v.bg,
          borderWidth: 1,
          borderColor: v.border,
          opacity: pressed ? 0.85 : 1,
          alignSelf: full ? 'stretch' : 'flex-start',
        },
        style,
      ]}>
      {icon ? <Ionicons name={icon} size={18} color={v.fg} /> : null}
      <AppText variant="bodyStrong" color={v.fg}>
        {label}
      </AppText>
    </Pressable>
  );
}

/** Inline pressable row used by lists; kept here so list affordances stay uniform. */
export function PressableRow({
  children,
  onPress,
}: {
  children: React.ReactNode;
  onPress?: () => void;
}) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}>
      <View>{children}</View>
    </Pressable>
  );
}
