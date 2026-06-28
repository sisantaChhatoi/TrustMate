import { Ionicons } from '@expo/vector-icons';
import { Pressable, View } from 'react-native';

import { AppText } from '@/components/ui/app-text';
import { TextField } from '@/components/ui/text-field';
import { colors, space } from '@/constants/design';
import { SignupErrors } from './types';

export function ContactStep({
  accent,
  name,
  setName,
  phone,
  setPhone,
  password,
  setPassword,
  showPassword,
  setShowPassword,
  errors,
}: {
  accent: string;
  name: string;
  setName: (v: string) => void;
  phone: string;
  setPhone: (v: string) => void;
  password: string;
  setPassword: (v: string) => void;
  showPassword: boolean;
  setShowPassword: (fn: (s: boolean) => boolean) => void;
  errors: SignupErrors;
}) {
  return (
    <View style={{ gap: space.lg }}>
      <TextField
        label="Full name"
        icon="person-circle-outline"
        placeholder="Your name"
        autoCapitalize="words"
        accent={accent}
        value={name}
        onChangeText={setName}
        error={errors.name}
      />
      <TextField
        label="Phone number"
        icon="call-outline"
        placeholder="10-digit mobile number"
        keyboardType="phone-pad"
        maxLength={10}
        accent={accent}
        value={phone}
        onChangeText={setPhone}
        error={errors.phone_no}
      />
      <View style={{ gap: space.sm }}>
        <TextField
          label="Password"
          icon="lock-closed-outline"
          placeholder="At least 6 characters"
          secureTextEntry={!showPassword}
          autoCapitalize="none"
          accent={accent}
          value={password}
          onChangeText={setPassword}
          error={errors.password}
        />
        <Pressable
          onPress={() => setShowPassword((s) => !s)}
          hitSlop={8}
          style={{ flexDirection: 'row', alignItems: 'center', gap: space.xs, alignSelf: 'flex-start' }}>
          <Ionicons
            name={showPassword ? 'eye-off-outline' : 'eye-outline'}
            size={15}
            color={colors.muted}
          />
          <AppText variant="caption">{showPassword ? 'Hide' : 'Show'} password</AppText>
        </Pressable>
      </View>
    </View>
  );
}
