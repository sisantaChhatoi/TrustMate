import { Ionicons } from '@expo/vector-icons';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AppText } from '@/components/ui/app-text';
import { BackHeader } from '@/components/ui/back-header';
import { Card } from '@/components/ui/card';
import { GradientPanel } from '@/components/ui/gradient-panel';
import { IconBadge } from '@/components/ui/icon-badge';
import { FraudMap } from '@/components/ui/fraud-map';
import { SectionHeader } from '@/components/ui/section-header';
import { colors, gradients, radius, space } from '@/constants/design';
import { api, type FraudHotspot, type FraudRing, type HighRiskAccount } from '@/lib/api';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

const RISK_COLOR: Record<string, string> = {
  high: colors.danger,
  medium: colors.amber,
  low: colors.success,
};
const RISK_TINT: Record<string, string> = {
  high: colors.dangerTint,
  medium: colors.amberTint,
  low: colors.successTint,
};
const ACCOUNT_ICON: Record<string, IconName> = {
  phone: 'call-outline',
  mule_account: 'card-outline',
  mule_upi: 'qr-code-outline',
};

function fmt(n: number) {
  if (n >= 1_00_00_000) return `₹${(n / 1_00_00_000).toFixed(1)}Cr`;
  if (n >= 1_00_000) return `₹${(n / 1_00_000).toFixed(1)}L`;
  if (n >= 1_000) return `₹${(n / 1_000).toFixed(0)}K`;
  return `₹${n}`;
}

function RiskBadge({ level }: { level: string }) {
  return (
    <View style={[styles.badge, { backgroundColor: RISK_TINT[level] ?? colors.brandTint }]}>
      <AppText variant="label" style={{ color: RISK_COLOR[level] ?? colors.brand }}>
        {level}
      </AppText>
    </View>
  );
}

function EmptyState({ icon, message }: { icon: IconName; message: string }) {
  return (
    <Card>
      <View style={{ alignItems: 'center', gap: space.sm, paddingVertical: space.lg }}>
        <Ionicons name={icon} size={28} color={colors.faint} />
        <AppText variant="caption" style={{ textAlign: 'center' }}>
          {message}
        </AppText>
      </View>
    </Card>
  );
}

function HotspotCard({ h }: { h: FraudHotspot }) {
  return (
    <View style={styles.row}>
      <View style={{ flex: 1, gap: 2 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
          <AppText variant="bodyStrong">{h.region}</AppText>
          <RiskBadge level={h.risk_level} />
        </View>
        <AppText variant="caption">{h.state}</AppText>
        {h.scam_types.length > 0 && (
          <AppText variant="caption" style={{ color: colors.faint }}>
            {h.scam_types.slice(0, 2).join(' · ')}
          </AppText>
        )}
      </View>
      <View style={{ alignItems: 'flex-end', gap: 2 }}>
        <AppText variant="bodyStrong">{h.incident_count}</AppText>
        <AppText variant="caption">reports</AppText>
        {h.total_amount_lost > 0 && (
          <AppText variant="caption" style={{ color: colors.danger }}>
            {fmt(h.total_amount_lost)} lost
          </AppText>
        )}
      </View>
    </View>
  );
}

function RingCard({ r, index }: { r: FraudRing; index: number }) {
  const entities = [...r.phone_numbers.slice(0, 2), ...r.mule_accounts.slice(0, 2)].slice(0, 3);

  return (
    <View style={styles.row}>
      <View
        style={[
          styles.ringIndex,
          { backgroundColor: index < 3 ? colors.brandTint : colors.border },
        ]}>
        <AppText variant="label" color={index < 3 ? colors.brand : colors.muted}>
          {index + 1}
        </AppText>
      </View>
      <View style={{ flex: 1, gap: 2 }}>
        <AppText variant="bodyStrong">
          {r.size} linked {r.size === 1 ? 'entity' : 'entities'}
        </AppText>
        <AppText variant="caption">
          {r.incident_count} {r.incident_count === 1 ? 'incident' : 'incidents'}
          {r.victim_regions.length > 0 ? ` · ${r.victim_regions.slice(0, 2).join(', ')}` : ''}
        </AppText>
        {entities.length > 0 && (
          <AppText variant="caption" style={{ color: colors.faint }} numberOfLines={1}>
            {entities.join(' · ')}
          </AppText>
        )}
      </View>
      {r.total_amount_demanded > 0 && (
        <AppText variant="caption" style={{ color: colors.amber }}>
          {fmt(r.total_amount_demanded)}
        </AppText>
      )}
    </View>
  );
}

function AccountRow({ a }: { a: HighRiskAccount }) {
  const icon = ACCOUNT_ICON[a.type] ?? 'alert-circle-outline';
  return (
    <View style={styles.row}>
      <IconBadge name={icon} tone="brand" size="sm" />
      <View style={{ flex: 1, gap: 2 }}>
        <AppText variant="bodyStrong" numberOfLines={1}>
          {a.value}
        </AppText>
        <AppText variant="caption">
          {a.type.replace(/_/g, ' ')} · {a.incident_count}{' '}
          {a.incident_count === 1 ? 'report' : 'reports'}
        </AppText>
      </View>
      <RiskBadge level={a.risk_level} />
    </View>
  );
}

export default function HotspotsScreen() {
  const [rings, setRings] = useState<FraudRing[]>([]);
  const [hotspots, setHotspots] = useState<FraudHotspot[]>([]);
  const [accounts, setAccounts] = useState<HighRiskAccount[]>([]);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([api.getRings(), api.getHotspots(), api.getHighRiskAccounts()])
      .then(([r, h, a]) => {
        setRings(r.rings ?? []);
        setHotspots(h.hotspots ?? []);
        setAccounts(a.accounts ?? []);
        setGeneratedAt(h.generated_at ?? r.generated_at ?? null);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  const hasData = rings.length > 0 || hotspots.length > 0 || accounts.length > 0;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top']}>
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{
          gap: space.lg,
          paddingHorizontal: space.lg,
          paddingBottom: space.huge,
        }}>
        <BackHeader
          title="Fraud hotspots"
          variant="title"
          titleStyle={{ fontSize: 19, lineHeight: 25 }}
          iconSize={21}
        />

        <View style={{ gap: space.lg }}>
          <GradientPanel colors={gradients.heroLight}>
            <AppText variant="heading" style={{ textAlign: 'center', color: '#403F4A' }}>
              Scam networks, mapped
            </AppText>
            <AppText variant="body" style={{ textAlign: 'center' }}>
              Live intelligence from the fraud graph — rings, hotspot cities, and flagged accounts
              built from real incident reports.
            </AppText>
            {generatedAt && (
              <AppText variant="caption" style={{ textAlign: 'center' }}>
                Updated {new Date(generatedAt).toLocaleDateString('en-IN', { dateStyle: 'medium' })}
              </AppText>
            )}
          </GradientPanel>

          {loading && (
            <View style={{ paddingVertical: space.huge, alignItems: 'center' }}>
              <ActivityIndicator color={colors.brand} />
            </View>
          )}

          {error && (
            <Card variant="danger">
              <AppText variant="body" color={colors.danger}>
                Could not load intelligence data. Make sure the server is running.
              </AppText>
            </Card>
          )}

          {!loading && !error && !hasData && (
            <Card>
              <View style={{ alignItems: 'center', gap: space.md, paddingVertical: space.lg }}>
                <Ionicons name="analytics-outline" size={36} color={colors.faint} />
                <AppText variant="body" style={{ textAlign: 'center' }}>
                  No intelligence data yet. The graph builds automatically after incidents are
                  reported via chat.
                </AppText>
              </View>
            </Card>
          )}

          {!loading && !error && hasData && (
            <>
              {/* Interactive map */}
              {hotspots.length > 0 && (
                <View style={{ gap: space.md }}>
                  <SectionHeader eyebrow="Hotspot map" icon="map-outline" />
                  <FraudMap hotspots={hotspots} />
                </View>
              )}

              {/* Hotspot cities */}
              <View style={{ gap: space.md }}>
                <SectionHeader eyebrow="Hotspot cities" icon="location-outline" />
                {hotspots.length === 0 ? (
                  <EmptyState icon="location-outline" message="No geocoded hotspots yet." />
                ) : (
                  <Card>
                    <View style={{ gap: space.lg }}>
                      {hotspots.slice(0, 10).map((h, i) => (
                        <View key={`${h.region}-${i}`} style={{ gap: space.lg }}>
                          {i > 0 && <View style={styles.divider} />}
                          <HotspotCard h={h} />
                        </View>
                      ))}
                    </View>
                  </Card>
                )}
              </View>

              {/* Fraud rings */}
              <View style={{ gap: space.md }}>
                <SectionHeader eyebrow="Fraud rings" icon="git-network-outline" />
                {rings.length === 0 ? (
                  <EmptyState icon="git-network-outline" message="No fraud rings detected yet." />
                ) : (
                  <Card>
                    <View style={{ gap: space.lg }}>
                      {rings.slice(0, 8).map((r, i) => (
                        <View key={r.ring_id} style={{ gap: space.lg }}>
                          {i > 0 && <View style={styles.divider} />}
                          <RingCard r={r} index={i} />
                        </View>
                      ))}
                    </View>
                  </Card>
                )}
              </View>

              {/* High-risk accounts */}
              <View style={{ gap: space.md }}>
                <SectionHeader eyebrow="High-risk accounts" icon="card-outline" />
                {accounts.length === 0 ? (
                  <EmptyState icon="card-outline" message="No high-risk accounts flagged yet." />
                ) : (
                  <Card>
                    <View style={{ gap: space.lg }}>
                      {accounts.slice(0, 10).map((a, i) => (
                        <View key={a.node} style={{ gap: space.lg }}>
                          {i > 0 && <View style={styles.divider} />}
                          <AccountRow a={a} />
                        </View>
                      ))}
                    </View>
                  </Card>
                )}
              </View>
            </>
          )}

          <AppText variant="caption" style={{ textAlign: 'center' }}>
            These are signals for awareness, not legal determinations.
          </AppText>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: space.sm,
    paddingVertical: 3,
    borderRadius: radius.pill,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.md,
  },
  divider: {
    height: 1,
    backgroundColor: colors.border,
  },
  ringIndex: {
    width: 28,
    height: 28,
    borderRadius: radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
