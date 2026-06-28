import { Ionicons } from '@expo/vector-icons';
import { Pressable, View } from 'react-native';

import { colors, radius, space } from '@/constants/design';

export function StepProgress({
  step,
  total,
  accent,
  onBack,
}: {
  step: number;
  total: number;
  accent: string;
  onBack: () => void;
}) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
      {step > 0 ? (
        <Pressable onPress={onBack} hitSlop={10}>
          <Ionicons name="chevron-back" size={22} color={colors.muted} />
        </Pressable>
      ) : null}
      <View style={{ flex: 1, flexDirection: 'row', gap: space.sm }}>
        {Array.from({ length: total }).map((_, i) => (
          <View
            key={i}
            style={{
              flex: 1,
              height: 5,
              borderRadius: radius.pill,
              backgroundColor: i <= step ? accent : colors.borderStrong,
            }}
          />
        ))}
      </View>
    </View>
  );
}
