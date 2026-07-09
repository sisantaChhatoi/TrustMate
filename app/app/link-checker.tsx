import { Ionicons } from '@expo/vector-icons';
import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';

import { AppText } from '@/components/ui/app-text';
import { BackHeader } from '@/components/ui/back-header';
import { Card } from '@/components/ui/card';
import { Screen } from '@/components/ui/screen';
import { colors, radius, space } from '@/constants/design';
import { api, type LinkCheckResult } from '@/lib/api';

export default function LinkCheckerScreen() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LinkCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const check = async () => {
    const trimmed = url.trim();
    if (!trimmed) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await api.checkLink(trimmed);
      setResult(res);
    } catch {
      setError('Could not check this link. Make sure it starts with http:// or https://');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen>
      <BackHeader title="Link checker" />

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <Card>
          <View style={{ gap: space.md }}>
            <AppText variant="caption">
              Paste a suspicious link to check it against Google Safe Browsing and VirusTotal.
            </AppText>
            <TextInput
              style={styles.input}
              value={url}
              onChangeText={setUrl}
              placeholder="https://example.com/suspicious-link"
              placeholderTextColor={colors.faint}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
              returnKeyType="go"
              onSubmitEditing={check}
            />
            <Pressable
              onPress={check}
              disabled={!url.trim() || loading}
              style={({ pressed }) => [
                styles.btn,
                { opacity: !url.trim() || loading ? 0.5 : pressed ? 0.8 : 1 },
              ]}>
              {loading ? (
                <ActivityIndicator size="small" color={colors.white} />
              ) : (
                <>
                  <Ionicons name="shield-checkmark-outline" size={18} color={colors.white} />
                  <AppText variant="bodyStrong" color={colors.white}>
                    Check link
                  </AppText>
                </>
              )}
            </Pressable>
          </View>
        </Card>
      </KeyboardAvoidingView>

      {error && (
        <Card variant="danger">
          <AppText variant="body" color={colors.danger}>
            {error}
          </AppText>
        </Card>
      )}

      {result && <ResultCard result={result} />}
    </Screen>
  );
}

function ResultCard({ result }: { result: LinkCheckResult }) {
  const safe = result.verdict === 'safe';
  const icon = safe ? 'checkmark-circle' : 'warning';
  const verdictColor = safe ? colors.success : colors.danger;
  const verdictBg = safe ? colors.successTint : colors.dangerTint;
  const verdictText = safe ? 'Safe' : 'Unsafe';

  return (
    <View style={{ gap: space.md }}>
      {/* Verdict banner */}
      <View style={[styles.banner, { backgroundColor: verdictBg }]}>
        <Ionicons name={icon} size={28} color={verdictColor} />
        <View style={{ flex: 1 }}>
          <AppText variant="subtitle" color={verdictColor}>
            {verdictText}
          </AppText>
          <AppText variant="caption" color={verdictColor} style={{ opacity: 0.8 }}>
            {result.url}
          </AppText>
        </View>
      </View>

      {/* Google Safe Browsing */}
      <Card>
        <View style={{ gap: space.sm }}>
          <View style={styles.sourceRow}>
            <Ionicons name="logo-google" size={16} color={colors.muted} />
            <AppText variant="bodyStrong">Google Safe Browsing</AppText>
            <StatusChip safe={result.google_safe_browsing.safe} />
          </View>
          {result.google_safe_browsing.threat && (
            <AppText variant="caption">
              Threat type: {result.google_safe_browsing.threat.replace(/_/g, ' ').toLowerCase()}
            </AppText>
          )}
        </View>
      </Card>

      {/* VirusTotal */}
      <Card>
        <View style={{ gap: space.sm }}>
          <View style={styles.sourceRow}>
            <Ionicons name="bug-outline" size={16} color={colors.muted} />
            <AppText variant="bodyStrong">VirusTotal</AppText>
            {result.virustotal.note === 'queued' ? (
              <View style={[styles.chip, { backgroundColor: colors.amberTint }]}>
                <AppText variant="label" color={colors.amber}>
                  Queued
                </AppText>
              </View>
            ) : (
              <StatusChip safe={result.virustotal.safe ?? true} />
            )}
          </View>
          {result.virustotal.note !== 'queued' && (
            <View style={{ flexDirection: 'row', gap: space.lg }}>
              <AppText variant="caption">
                Malicious:{' '}
                <AppText variant="caption" color={result.virustotal.malicious > 0 ? colors.danger : colors.success}>
                  {result.virustotal.malicious}
                </AppText>
              </AppText>
              <AppText variant="caption">
                Suspicious:{' '}
                <AppText variant="caption" color={result.virustotal.suspicious > 0 ? colors.amber : colors.success}>
                  {result.virustotal.suspicious}
                </AppText>
              </AppText>
            </View>
          )}
          {result.virustotal.note === 'queued' && (
            <AppText variant="caption">
              URL submitted for scanning. Check back in a few minutes.
            </AppText>
          )}
        </View>
      </Card>
    </View>
  );
}

function StatusChip({ safe }: { safe: boolean }) {
  return (
    <View style={[styles.chip, { backgroundColor: safe ? colors.successTint : colors.dangerTint }]}>
      <AppText variant="label" color={safe ? colors.success : colors.danger}>
        {safe ? 'Clean' : 'Flagged'}
      </AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  input: {
    backgroundColor: colors.bg,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    fontSize: 14,
    color: colors.ink,
  },
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: space.sm,
    backgroundColor: colors.brand,
    borderRadius: radius.md,
    paddingVertical: 14,
  },
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.md,
    padding: space.lg,
    borderRadius: radius.xl,
  },
  sourceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
  },
  chip: {
    marginLeft: 'auto',
    paddingHorizontal: space.sm,
    paddingVertical: 3,
    borderRadius: radius.pill,
  },
});
