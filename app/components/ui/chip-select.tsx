import { Ionicons } from '@expo/vector-icons';
import { Pressable, View } from 'react-native';

import { colors, radius, space } from '@/constants/design';
import { AppText } from './app-text';

// First pick is primary (badged), then secondary/tertiary, capped at `max`.
export function ChipSelect({
  options,
  value,
  onChange,
  max = 3,
}: {
  options: string[];
  value: string[];
  onChange: (next: string[]) => void;
  max?: number;
}) {
  const toggle = (opt: string) => {
    if (value.includes(opt)) {
      onChange(value.filter((v) => v !== opt));
    } else if (value.length < max) {
      onChange([...value, opt]);
    }
  };

  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
      {options.map((opt) => {
        const rank = value.indexOf(opt);
        const selected = rank >= 0;
        const atCap = value.length >= max;
        const disabled = !selected && atCap;
        return (
          <Pressable
            key={opt}
            onPress={() => toggle(opt)}
            style={({ pressed }) => ({
              flexDirection: 'row',
              alignItems: 'center',
              gap: space.xs,
              paddingVertical: space.sm,
              paddingHorizontal: space.lg,
              borderRadius: radius.pill,
              borderWidth: 1.5,
              borderColor: selected ? colors.brand : colors.border,
              backgroundColor: selected ? colors.brandTint : colors.surface,
              opacity: disabled ? 0.4 : pressed ? 0.8 : 1,
            })}>
            {selected ? (
              <Ionicons name="checkmark" size={14} color={colors.brand} />
            ) : null}
            <AppText variant="bodyStrong" color={selected ? colors.brand : colors.body}>
              {opt}
            </AppText>
            {rank === 0 ? (
              <AppText variant="label" color={colors.brand} style={{ marginLeft: space.xs }}>
                Primary
              </AppText>
            ) : null}
          </Pressable>
        );
      })}
    </View>
  );
}