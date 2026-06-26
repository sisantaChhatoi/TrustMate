import { StyleProp, View, ViewStyle } from 'react-native';

import { colors, radius, shadow, space } from '@/constants/design';

type Variant = 'default' | 'flat' | 'danger';

const VARIANTS: Record<Variant, ViewStyle> = {
  default: { backgroundColor: colors.surface, borderColor: colors.border, ...shadow.card },
  flat: { backgroundColor: colors.surface, borderColor: colors.border },
  danger: { backgroundColor: colors.dangerTint, borderColor: colors.dangerBorder },
};

/** Standard surface container. Consistent radius, border, padding and elevation. */
export function Card({
  children,
  variant = 'default',
  style,
}: {
  children: React.ReactNode;
  variant?: Variant;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <View
      style={[
        { borderRadius: radius.xl, borderWidth: 1, padding: space.lg },
        VARIANTS[variant],
        style,
      ]}>
      {children}
    </View>
  );
}
