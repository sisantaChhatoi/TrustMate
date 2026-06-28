import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { FormBackdrop } from '@/components/signup/form-backdrop';
import { AppText } from '@/components/ui/app-text';
import { TextField } from '@/components/ui/text-field';
import { APP_NAME } from '@/constants/app';
import { colors, radius, space } from '@/constants/design';
import { flags } from '@/constants/flags';
import { api, ApiError } from '@/lib/api';
import { saveToken } from '@/lib/auth';

const ACCENT = colors.brand;

export default function Login() {
  const router = useRouter();

  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async () => {
    setError(null);
    if (!phone.trim() || !password) {
      setError('Enter your phone number and password.');
      return;
    }
    if (flags.debugLoginForm) {
      console.log('debug login (no-op)', { phone: phone.trim() });
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.login(phone.trim(), password);
      await saveToken(res.access_token);
      router.replace('/(tabs)');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <FormBackdrop accent={ACCENT} icon="shield-checkmark" />

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView
          contentContainerStyle={{
            paddingHorizontal: 28,
            paddingTop: space.xl,
            paddingBottom: space.huge,
            gap: space.xxl,
          }}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}>
          <View style={{ gap: space.xs, marginTop: space.xl }}>
            <AppText variant="label" color={ACCENT}>
              Sign in
            </AppText>
            <AppText variant="title">Welcome back</AppText>
            <AppText variant="body">Sign in to keep {APP_NAME} protecting your calls.</AppText>
          </View>

          <View style={{ gap: space.lg }}>
            <TextField
              label="Phone number"
              icon="call-outline"
              placeholder="10-digit mobile number"
              keyboardType="phone-pad"
              maxLength={10}
              accent={ACCENT}
              value={phone}
              onChangeText={setPhone}
            />
            <View style={{ gap: space.sm }}>
              <TextField
                label="Password"
                icon="lock-closed-outline"
                placeholder="Your password"
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                accent={ACCENT}
                value={password}
                onChangeText={setPassword}
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

          <View style={{ gap: space.md }}>
            {error ? (
              <View style={styles.errorBox}>
                <Ionicons name="alert-circle" size={18} color={colors.danger} />
                <AppText variant="caption" color={colors.danger} style={{ flex: 1 }}>
                  {error}
                </AppText>
              </View>
            ) : null}
            <Pressable
              onPress={onSubmit}
              disabled={submitting}
              style={({ pressed }) => [
                styles.cta,
                { backgroundColor: ACCENT, opacity: submitting ? 0.7 : pressed ? 0.9 : 1 },
              ]}>
              {submitting ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <>
                  <AppText variant="bodyStrong" color="#FFFFFF">
                    Sign in
                  </AppText>
                  <Ionicons name="arrow-forward" size={18} color="#FFFFFF" />
                </>
              )}
            </Pressable>

            <Pressable
              onPress={() => router.replace('/signup')}
              hitSlop={8}
              style={{ alignSelf: 'center', paddingVertical: space.sm }}>
              <AppText variant="caption">
                New here? <AppText variant="link">Create a profile</AppText>
              </AppText>
            </Pressable>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    backgroundColor: colors.dangerTint,
    borderWidth: 1,
    borderColor: colors.dangerBorder,
    borderRadius: radius.md,
    padding: space.md,
  },
  cta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: space.sm,
    paddingVertical: 16,
    borderRadius: radius.md,
  },
});
