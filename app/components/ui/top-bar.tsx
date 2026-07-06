import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Modal, Pressable, View, StyleSheet } from 'react-native';

import { APP_NAME } from '@/constants/app';
import { colors, radius, space } from '@/constants/design';
import { api, type UserPublic } from '@/lib/api';
import { clearToken } from '@/lib/auth';
import { AppText } from './app-text';
import { IconBadge } from './icon-badge';

let _userCache: UserPublic | null = null;

export function TopBar({ title }: { title?: string }) {
  const [user, setUser] = useState<UserPublic | null>(_userCache);
  const [showProfile, setShowProfile] = useState(false);

  useEffect(() => {
    if (_userCache) return;
    api
      .me()
      .then((u) => {
        _userCache = u;
        setUser(u);
      })
      .catch(() => null);
  }, []);

  const initial = user?.name?.[0]?.toUpperCase() ?? '?';

  return (
    <>
      <View style={styles.bar}>
        <View style={styles.left}>
          <IconBadge name="shield-checkmark" tone="brand" size="sm" />
          <AppText variant="heading">{title ?? APP_NAME}</AppText>
        </View>
        <View style={styles.right}>
          <Pressable
            hitSlop={8}
            // @ts-ignore hidden tab (href:null) is excluded from typed routes
            onPress={() => router.navigate('/(tabs)/alerts')}
            style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}>
            <Ionicons name="notifications-outline" size={22} color={colors.muted} />
          </Pressable>
          <Pressable
            hitSlop={8}
            onPress={() => setShowProfile(true)}
            style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}>
            <View style={styles.avatar}>
              <AppText variant="label" color={colors.white}>
                {initial}
              </AppText>
            </View>
          </Pressable>
        </View>
      </View>

      <Modal
        visible={showProfile}
        transparent
        animationType="fade"
        onRequestClose={() => setShowProfile(false)}>
        <Pressable style={styles.backdrop} onPress={() => setShowProfile(false)}>
          <Pressable style={styles.card} onPress={() => {}}>
            <View style={styles.profileHeader}>
              <View style={styles.avatarLg}>
                <AppText variant="heading" color={colors.white}>
                  {initial}
                </AppText>
              </View>
              <View style={{ flex: 1 }}>
                <AppText variant="subtitle">{user?.name ?? '—'}</AppText>
                <AppText variant="caption">{user?.phone_no ?? '—'}</AppText>
              </View>
            </View>

            {user && (
              <View style={styles.details}>
                <DetailRow label="City" value={user.city} />
                <DetailRow label="State" value={user.state} />
                <DetailRow label="PIN" value={user.pin} />
              </View>
            )}

            <Pressable
              style={styles.logoutBtn}
              onPress={async () => {
                _userCache = null;
                await clearToken();
                setShowProfile(false);
                router.replace('/onboarding');
              }}>
              <Ionicons name="log-out-outline" size={16} color={colors.danger} />
              <AppText variant="bodyStrong" color={colors.danger}>
                Sign out
              </AppText>
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.detailRow}>
      <AppText variant="caption">{label}</AppText>
      <AppText variant="bodyStrong">{value}</AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  left: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  right: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  avatar: {
    width: 34,
    height: 34,
    borderRadius: radius.pill,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  card: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    padding: space.xxl,
    gap: space.xl,
  },
  profileHeader: { flexDirection: 'row', alignItems: 'center', gap: space.lg },
  avatarLg: {
    width: 52,
    height: 52,
    borderRadius: radius.pill,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  details: { gap: space.sm },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: space.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    paddingVertical: space.md,
  },
});
