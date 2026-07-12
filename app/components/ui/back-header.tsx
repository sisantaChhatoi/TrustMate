import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Pressable, StyleProp, TextStyle, View } from 'react-native';

import { colors, space, type TypeVariant } from '@/constants/design';
import { AppText } from './app-text';

export function BackHeader({
  title,
  variant = 'heading',
  titleStyle,
  iconSize = 26,
}: {
  title: string;
  variant?: TypeVariant;
  titleStyle?: StyleProp<TextStyle>;
  iconSize?: number;
}) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
      <Pressable
        hitSlop={8}
        onPress={() => router.back()}
        style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, marginLeft: -4 })}>
        <Ionicons name="chevron-back" size={iconSize} color={colors.ink} />
      </Pressable>
      <AppText variant={variant} style={titleStyle}>
        {title}
      </AppText>
    </View>
  );
}
