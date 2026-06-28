import { Ionicons } from '@expo/vector-icons';
import { useState } from 'react';
import { TextInput, TextInputProps, View } from 'react-native';

import { colors, radius, space, typography } from '@/constants/design';
import { AppText } from './app-text';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

type Props = TextInputProps & {
  label: string;
  icon?: IconName;
  error?: string | null;
  optional?: boolean;
  accent?: string;
};

export function TextField({ label, icon, error, optional, accent = colors.brand, style, ...input }: Props) {
  const [focused, setFocused] = useState(false);
  const borderColor = error ? colors.danger : focused ? accent : colors.border;

  return (
    <View style={{ gap: space.sm }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
        <AppText variant="label" color={colors.muted}>
          {label}
        </AppText>
        {optional ? (
          <AppText variant="label" color={colors.faint}>
            Optional
          </AppText>
        ) : null}
      </View>

      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: space.sm,
          backgroundColor: colors.surface,
          borderWidth: 1.5,
          borderColor,
          borderRadius: radius.md,
          paddingHorizontal: space.lg,
          height: 52,
        }}>
        {icon ? (
          <Ionicons name={icon} size={18} color={focused ? accent : colors.faint} />
        ) : null}
        <TextInput
          {...input}
          onFocus={(e) => {
            setFocused(true);
            input.onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            input.onBlur?.(e);
          }}
          placeholderTextColor={colors.faint}
          style={[
            { flex: 1, paddingVertical: 0, color: colors.ink },
            { fontSize: typography.body.fontSize, fontWeight: typography.body.fontWeight },
            style,
          ]}
        />
      </View>

      {error ? (
        <AppText variant="caption" color={colors.danger}>
          {error}
        </AppText>
      ) : null}
    </View>
  );
}
