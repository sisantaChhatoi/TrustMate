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
              Paste a suspicious link to check it for scam signals, phishing patterns, and known
              threats.
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

function riskColor(level: LinkCheckResult['risk_level']): string {
  if (level === 'high') return colors.danger;
  if (level === 'suspicious') return colors.amber;
  return colors.success;
}

function riskBg(level: LinkCheckResult['risk_level']): string {
  if (level === 'high') return colors.dangerTint;
  if (level === 'suspicious') return colors.amberTint;
  return colors.successTint;
}

function verdictLabel(verdict: LinkCheckResult['verdict']): string {
  if (verdict === 'unsafe') return 'Unsafe';
  if (verdict === 'suspicious') return 'Suspicious';
  return 'Safe';
}

function verdictIcon(
  verdict: LinkCheckResult['verdict'],
): 'warning' | 'alert-circle' | 'checkmark-circle' {
  if (verdict === 'unsafe') return 'warning';
  if (verdict === 'suspicious') return 'alert-circle';
  return 'checkmark-circle';
}

function ResultCard({ result }: { result: LinkCheckResult }) {
  const clr = riskColor(result.risk_level);
  const bg = riskBg(result.risk_level);

  return (
    <View style={{ gap: space.md }}>
      {/* Verdict banner */}
      <View style={[styles.banner, { backgroundColor: bg }]}>
        <Ionicons name={verdictIcon(result.verdict)} size={28} color={clr} />
        <View style={{ flex: 1 }}>
          <AppText variant="subtitle" color={clr}>
            {verdictLabel(result.verdict)}
          </AppText>
          <AppText variant="caption" color={clr} style={{ opacity: 0.8 }} numberOfLines={1}>
            {result.url}
          </AppText>
        </View>
      </View>

      {/* Risk score bar */}
      <Card>
        <View style={{ gap: space.sm }}>
          <View
            style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
            <AppText variant="bodyStrong">Risk score</AppText>
            <AppText variant="bodyStrong" color={clr}>
              {result.risk_score}/100
            </AppText>
          </View>
          <View style={styles.barTrack}>
            <View
              style={[
                styles.barFill,
                { width: `${result.risk_score}%` as `${number}%`, backgroundColor: clr },
              ]}
            />
          </View>
          <AppText variant="caption" color={colors.muted}>
            {result.risk_level === 'low'
              ? 'No significant risk signals detected'
              : result.risk_level === 'suspicious'
                ? 'Suspicious patterns detected — proceed with caution'
                : 'High-risk — do not open this link'}
          </AppText>
        </View>
      </Card>

      {/* Resolved URL (if shortener was expanded) */}
      {result.resolved_url && (
        <Card>
          <View style={{ gap: space.xs }}>
            <View style={styles.sourceRow}>
              <Ionicons name="link-outline" size={16} color={colors.muted} />
              <AppText variant="bodyStrong">Resolved destination</AppText>
            </View>
            <AppText variant="caption" color={colors.muted} numberOfLines={2}>
              {result.resolved_url}
            </AppText>
            <AppText variant="caption" color={colors.amber}>
              Shortener detected — the link above is the real destination
            </AppText>
          </View>
        </Card>
      )}

      {/* Heuristic flags */}
      {result.flags?.length > 0 && (
        <Card>
          <View style={{ gap: space.sm }}>
            <View style={styles.sourceRow}>
              <Ionicons name="alert-circle-outline" size={16} color={colors.muted} />
              <AppText variant="bodyStrong">Warning signals</AppText>
            </View>
            {result.flags.map((flag, i) => (
              <View key={i} style={styles.flagRow}>
                <Ionicons name="chevron-forward" size={12} color={clr} />
                <AppText variant="caption" style={{ flex: 1 }}>
                  {flag}
                </AppText>
              </View>
            ))}
          </View>
        </Card>
      )}

      {/* Domain Age */}
      {result.domain_age && (
        <Card>
          <View style={{ gap: space.sm }}>
            <View style={styles.sourceRow}>
              <Ionicons name="calendar-outline" size={16} color={colors.muted} />
              <AppText variant="bodyStrong">Domain age</AppText>
              {result.domain_age.age_days !== null && (
                <View
                  style={[
                    styles.chip,
                    {
                      backgroundColor:
                        result.domain_age.age_days < 30
                          ? colors.dangerTint
                          : result.domain_age.age_days < 90
                            ? colors.amberTint
                            : colors.successTint,
                    },
                  ]}>
                  <AppText
                    variant="label"
                    color={
                      result.domain_age.age_days < 30
                        ? colors.danger
                        : result.domain_age.age_days < 90
                          ? colors.amber
                          : colors.success
                    }>
                    {result.domain_age.age_days < 30
                      ? `${result.domain_age.age_days}d old`
                      : result.domain_age.age_days < 365
                        ? `${result.domain_age.age_days}d old`
                        : `${Math.floor(result.domain_age.age_days / 365)}y old`}
                  </AppText>
                </View>
              )}
            </View>
            {result.domain_age.age_days !== null ? (
              <AppText variant="caption" color={colors.muted}>
                {result.domain_age.domain} registered on {result.domain_age.created}
                {result.domain_age.age_days < 30
                  ? ' — very new domain, high scam risk'
                  : result.domain_age.age_days < 90
                    ? ' — less than 3 months old'
                    : ' — established domain'}
              </AppText>
            ) : (
              <AppText variant="caption" color={colors.muted}>
                Could not determine domain age
              </AppText>
            )}
          </View>
        </Card>
      )}

      {/* ML Classifier */}
      {result.ml_classifier?.available &&
        result.ml_classifier.label &&
        (result.ml_classifier.confidence ?? 0) >= 0.8 && (
          <Card>
            <View style={{ gap: space.sm }}>
              <View style={styles.sourceRow}>
                <Ionicons name="hardware-chip-outline" size={16} color={colors.muted} />
                <AppText variant="bodyStrong">ML classifier</AppText>
                <View
                  style={[
                    styles.chip,
                    {
                      backgroundColor:
                        result.ml_classifier.label === 'benign'
                          ? colors.successTint
                          : colors.dangerTint,
                    },
                  ]}>
                  <AppText
                    variant="label"
                    color={
                      result.ml_classifier.label === 'benign' ? colors.success : colors.danger
                    }>
                    {result.ml_classifier.label}
                  </AppText>
                </View>
              </View>
              <AppText variant="caption" color={colors.muted}>
                Confidence: {((result.ml_classifier.confidence ?? 0) * 100).toFixed(0)}%
              </AppText>
            </View>
          </Card>
        )}

      {/* Page Analysis */}
      {result.page_analysis?.available && (
        <Card>
          <View style={{ gap: space.sm }}>
            <View style={styles.sourceRow}>
              <Ionicons name="document-text-outline" size={16} color={colors.muted} />
              <AppText variant="bodyStrong">Page analysis</AppText>
              <StatusChip safe={result.page_analysis.flags.length === 0} />
            </View>
            {result.page_analysis.flags.length > 0 ? (
              result.page_analysis.flags.map((flag, i) => (
                <View key={i} style={styles.flagRow}>
                  <Ionicons name="chevron-forward" size={12} color={colors.danger} />
                  <AppText variant="caption" style={{ flex: 1 }}>
                    {flag}
                  </AppText>
                </View>
              ))
            ) : (
              <AppText variant="caption" color={colors.muted}>
                No suspicious form or content detected
              </AppText>
            )}
          </View>
        </Card>
      )}

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
            {result.virustotal.note === 'queued' || result.virustotal.note === 'unavailable' ? (
              <View style={[styles.chip, { backgroundColor: colors.amberTint }]}>
                <AppText variant="label" color={colors.amber}>
                  {result.virustotal.note === 'queued' ? 'Queued' : 'Unavailable'}
                </AppText>
              </View>
            ) : (
              <StatusChip safe={result.virustotal.safe ?? true} />
            )}
          </View>
          {result.virustotal.note !== 'queued' && result.virustotal.note !== 'unavailable' && (
            <View style={{ flexDirection: 'row', gap: space.lg }}>
              <AppText variant="caption">
                Malicious:{' '}
                <AppText
                  variant="caption"
                  color={result.virustotal.malicious > 0 ? colors.danger : colors.success}>
                  {result.virustotal.malicious}
                </AppText>
              </AppText>
              <AppText variant="caption">
                Suspicious:{' '}
                <AppText
                  variant="caption"
                  color={result.virustotal.suspicious > 0 ? colors.amber : colors.success}>
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
  flagRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: space.xs,
  },
  chip: {
    marginLeft: 'auto',
    paddingHorizontal: space.sm,
    paddingVertical: 3,
    borderRadius: radius.pill,
  },
  barTrack: {
    height: 8,
    borderRadius: radius.pill,
    backgroundColor: colors.border,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: radius.pill,
  },
});
