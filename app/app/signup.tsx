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

import { ContactStep } from '@/components/signup/contact-step';
import { FormBackdrop } from '@/components/signup/form-backdrop';
import { LanguageStep } from '@/components/signup/language-step';
import { RegionStep } from '@/components/signup/region-step';
import { StepProgress } from '@/components/signup/step-progress';
import { SignupErrors } from '@/components/signup/types';
import { AppText } from '@/components/ui/app-text';
import { colors, radius, space } from '@/constants/design';
import { flags } from '@/constants/flags';
import { api, ApiError } from '@/lib/api';
import { saveToken } from '@/lib/auth';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

const STEPS: { label: string; accent: string; icon: IconName; title: string; subtitle: string }[] = [
  {
    label: 'Step 1 of 3',
    accent: '#D97706',
    icon: 'shield-checkmark',
    title: 'Let’s get you set up',
    subtitle: 'Your name, number, and a password to secure your account.',
  },
  {
    label: 'Step 2 of 3',
    accent: '#7C3AED',
    icon: 'language-outline',
    title: 'Languages you speak',
    subtitle: 'Pick up to three — the first is your primary. We listen for scams in these.',
  },
  {
    label: 'Step 3 of 3',
    accent: '#0D9488',
    icon: 'location-outline',
    title: 'Where you’re based',
    subtitle: 'Helps us tune protection to your region.',
  },
];

export default function Signup() {
  const router = useRouter();

  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [languages, setLanguages] = useState<string[]>([]);
  const [age, setAge] = useState('');
  const [state, setState] = useState('');
  const [city, setCity] = useState('');
  const [pin, setPin] = useState('');
  const [errors, setErrors] = useState<SignupErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const meta = STEPS[step];
  const isLast = step === STEPS.length - 1;

  const validateStep = (s: number): SignupErrors => {
    const e: SignupErrors = {};
    if (s === 0) {
      if (!name.trim()) e.name = 'Enter your name';
      if (!/^\d{10}$/.test(phone.trim())) e.phone_no = 'Enter a valid 10-digit phone number';
      if (password.length < 6) e.password = 'At least 6 characters';
    } else if (s === 1) {
      if (languages.length === 0) e.languages = 'Pick at least one language';
    } else {
      const ageNum = Number(age);
      if (!age || !Number.isInteger(ageNum) || ageNum <= 0) e.age = 'Enter a valid age';
      if (!state.trim()) e.state = 'Required';
      if (!city.trim()) e.city = 'Required';
      if (!/^\d{6}$/.test(pin.trim())) e.pin = 'Enter a 6-digit PIN code';
    }
    return e;
  };

  const onBack = () => {
    setErrors({});
    setFormError(null);
    if (step > 0) setStep(step - 1);
    else router.back();
  };

  const onNext = () => {
    setFormError(null);
    const e = validateStep(step);
    setErrors(e);
    if (Object.keys(e).length > 0) return;
    if (!isLast) {
      setStep(step + 1);
      return;
    }
    void onSubmit();
  };

  const onSubmit = async () => {
    // Shape matches the backend UserCreate schema.
    const payload = {
      name: name.trim(),
      phone_no: phone.trim(),
      password,
      age: Number(age),
      state: state.trim(),
      city: city.trim(),
      pin: pin.trim(),
      languages: {
        primary: languages[0],
        secondary: languages[1] ?? null,
        tertiary: languages[2] ?? null,
      },
    };

    if (flags.debugSignupForm) {
      console.log('debug signup payload (no-op)', payload);
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.signup(payload);
      await saveToken(res.access_token);
      router.replace('/(tabs)');
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : 'Something went wrong. Please try again.';
      setFormError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <FormBackdrop accent={meta.accent} icon={meta.icon} />

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
          {/* Progress + header */}
          <View style={{ gap: space.lg }}>
            <StepProgress step={step} total={STEPS.length} accent={meta.accent} onBack={onBack} />
            <View style={{ gap: space.xs }}>
              <AppText variant="label" color={meta.accent}>
                {meta.label}
              </AppText>
              <AppText variant="title">{meta.title}</AppText>
              <AppText variant="body">{meta.subtitle}</AppText>
            </View>
          </View>

          {step === 0 ? (
            <ContactStep
              accent={meta.accent}
              name={name}
              setName={setName}
              phone={phone}
              setPhone={setPhone}
              password={password}
              setPassword={setPassword}
              showPassword={showPassword}
              setShowPassword={setShowPassword}
              errors={errors}
            />
          ) : null}

          {step === 1 ? (
            <LanguageStep languages={languages} setLanguages={setLanguages} errors={errors} />
          ) : null}

          {step === 2 ? (
            <RegionStep
              accent={meta.accent}
              age={age}
              setAge={setAge}
              state={state}
              setState={setState}
              city={city}
              setCity={setCity}
              pin={pin}
              setPin={setPin}
              errors={errors}
            />
          ) : null}

          {/* Controls */}
          <View style={{ gap: space.md }}>
            {formError ? (
              <View style={styles.errorBox}>
                <Ionicons name="alert-circle" size={18} color={colors.danger} />
                <AppText variant="caption" color={colors.danger} style={{ flex: 1 }}>
                  {formError}
                </AppText>
              </View>
            ) : null}
            <View style={{ flexDirection: 'row', gap: space.md }}>
              {step > 0 ? (
                <Pressable onPress={onBack} style={({ pressed }) => [styles.back, { opacity: pressed ? 0.7 : 1 }]}>
                  <Ionicons name="arrow-back" size={18} color={colors.ink} />
                </Pressable>
              ) : null}
              <Pressable
                onPress={onNext}
                disabled={submitting}
                style={({ pressed }) => [
                  styles.cta,
                  { backgroundColor: meta.accent, opacity: submitting ? 0.7 : pressed ? 0.9 : 1 },
                ]}>
                {submitting ? (
                  <ActivityIndicator color="#FFFFFF" />
                ) : (
                  <>
                    <AppText variant="bodyStrong" color="#FFFFFF">
                      {isLast ? 'Create profile' : 'Continue'}
                    </AppText>
                    <Ionicons name="arrow-forward" size={18} color="#FFFFFF" />
                  </>
                )}
              </Pressable>
            </View>
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
  back: {
    width: 52,
    height: 52,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cta: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: space.sm,
    paddingVertical: 16,
    borderRadius: radius.md,
  },
});
