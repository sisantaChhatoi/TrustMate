import { StyleProp, Text, TextProps, TextStyle } from 'react-native';

import { TypeVariant, typography } from '@/constants/design';

type AppTextProps = TextProps & {
  variant?: TypeVariant;
  color?: string;
  style?: StyleProp<TextStyle>;
};

/**
 * The only text component the app uses. Variants come from the type scale so
 * size/weight/leading/color stay consistent. Pass `color` only when a specific
 * piece of text genuinely needs it (rare — keep text near-monochrome).
 */
export function AppText({ variant = 'body', color, style, ...rest }: AppTextProps) {
  return <Text {...rest} style={[typography[variant], color ? { color } : null, style]} />;
}
