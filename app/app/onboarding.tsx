import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  NativeScrollEvent,
  NativeSyntheticEvent,
  Pressable,
  StatusBar,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';
import Animated, {
  Extrapolation,
  interpolate,
  SharedValue,
  useAnimatedScrollHandler,
  useAnimatedStyle,
  useSharedValue,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { CallFlowArt, GraphArt, MapArt, RadarArt } from '@/components/onboarding/onboarding-art';
import { AppText } from '@/components/ui/app-text';
import { colors } from '@/constants/design';
import { flags } from '@/constants/flags';
import { resolveStartRoute } from '@/lib/session';

const PAGE_BG = '#F7F8FC';
const AUTOPLAY_MS = 4600;

type Slide = {
  key: string;
  Art: () => React.ReactElement;
  accent: string;
  tint: string;
  eyebrow: string;
  title: string;
  subtitle: string;
};

const SLIDES: Slide[] = [
  {
    key: 'call',
    Art: CallFlowArt,
    accent: '#4F46E5',
    tint: '#EEF1FF',
    eyebrow: 'Call protection',
    title: 'Scams stopped mid-call',
    subtitle:
      'Our agent joins the line, spots fraud passing between you and the scammer, and steps in instantly.',
  },
  {
    key: 'chat',
    Art: GraphArt,
    accent: '#7C3AED',
    tint: '#F3EEFF',
    eyebrow: 'Chat risk checks',
    title: 'Ask before you trust',
    subtitle:
      'Describe anything suspicious — a message, link, or caller — and our graph intelligence traces the connections to score the risk.',
  },
  {
    key: 'geo',
    Art: MapArt,
    accent: '#0D9488',
    tint: '#E7FBF6',
    eyebrow: 'Geospatial intelligence',
    title: 'See where fraud lives',
    subtitle:
      'Live cybercrime hotspots mapped across India, so you know which numbers and regions to watch.',
  },
  {
    key: 'evolve',
    Art: RadarArt,
    accent: '#D97706',
    tint: '#FFF6E6',
    eyebrow: 'Always learning',
    title: 'Ahead of new scams',
    subtitle:
      'The system constantly studies the latest fraud patterns, so your protection evolves as fast as the scammers do.',
  },
];

export default function Onboarding() {
  const { width, height } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const scrollX = useSharedValue(0);
  const listRef = useRef<FlatList<Slide>>(null);
  const idxRef = useRef(0);
  const [index, setIndex] = useState(0);
  const [resolving, setResolving] = useState(true);

  const onScroll = useAnimatedScrollHandler((e) => {
    scrollX.value = e.contentOffset.x;
  });

  const goTo = useCallback(
    (i: number) => {
      listRef.current?.scrollToOffset({ offset: i * width, animated: true });
      idxRef.current = i;
      setIndex(i);
    },
    [width],
  );

  useEffect(() => {
    const id = setInterval(() => goTo((idxRef.current + 1) % SLIDES.length), AUTOPLAY_MS);
    return () => clearInterval(id);
  }, [goTo, index]);

  useEffect(() => {
    resolveStartRoute().then((dest) => {
      if (dest !== '/signup') {
        router.replace(dest);
      } else {
        setResolving(false);
      }
    });
  }, [router]);

  const onMomentumEnd = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const i = Math.round(e.nativeEvent.contentOffset.x / width);
    idxRef.current = i;
    setIndex(i);
  };

  const finish = async () => {
    if (resolving) return;
    if (flags.debugLoginForm) {
      router.replace('/login');
      return;
    }
    if (flags.debugSignupForm) {
      router.replace('/signup');
      return;
    }
    setResolving(true);
    const dest = await resolveStartRoute();
    router.replace(dest);
  };
  const isLast = index === SLIDES.length - 1;
  const active = SLIDES[index];

  if (resolving) {
    return (
      <View
        style={{
          flex: 1,
          backgroundColor: PAGE_BG,
          alignItems: 'center',
          justifyContent: 'center',
        }}>
        <ActivityIndicator size="large" color={colors.brand} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: PAGE_BG }}>
      <StatusBar barStyle="dark-content" />

      <Animated.FlatList
        ref={listRef}
        data={SLIDES}
        keyExtractor={(s) => s.key}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={onScroll}
        scrollEventThrottle={16}
        onMomentumScrollEnd={onMomentumEnd}
        renderItem={({ item }) => (
          <SlideView item={item} width={width} height={height} topInset={insets.top} />
        )}
      />

      <Pressable
        onPress={finish}
        hitSlop={8}
        style={{ position: 'absolute', top: insets.top + 6, right: 18, padding: 8 }}>
        <AppText variant="bodyStrong" color={colors.muted}>
          Skip
        </AppText>
      </Pressable>

      {/* Bottom controls with a soft mask so copy never collides with them */}
      <View style={[styles.controls, { paddingBottom: insets.bottom + 22 }]}>
        <LinearGradient
          colors={['rgba(247,248,252,0)', PAGE_BG]}
          style={StyleSheet.absoluteFill}
          pointerEvents="none"
        />
        <View style={styles.dots}>
          {SLIDES.map((_, i) => (
            <Dot key={i} i={i} scrollX={scrollX} width={width} accent={active.accent} />
          ))}
        </View>
        <Pressable
          onPress={() => (isLast ? finish() : goTo(index + 1))}
          style={({ pressed }) => ({ opacity: pressed ? 0.9 : 1 })}>
          <LinearGradient
            colors={[active.accent, '#7C3AED']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.cta}>
            {resolving ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <AppText variant="bodyStrong" color="#FFFFFF">
                  {isLast ? 'Get Started' : 'Continue'}
                </AppText>
                <Ionicons name="arrow-forward" size={18} color="#FFFFFF" />
              </>
            )}
          </LinearGradient>
        </Pressable>
      </View>
    </View>
  );
}

function SlideView({
  item,
  width,
  height,
  topInset,
}: {
  item: Slide;
  width: number;
  height: number;
  topInset: number;
}) {
  const { Art } = item;
  const heroH = height * 0.56;
  return (
    <View style={{ width, height }}>
      {/* Colored illustration hero */}
      <View style={{ height: heroH, paddingTop: topInset }}>
        <LinearGradient colors={[item.tint, PAGE_BG]} style={StyleSheet.absoluteFill} />
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
          <Art />
        </View>
        {/* mask: fade the hero into the page */}
        <LinearGradient
          colors={['transparent', PAGE_BG]}
          style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 110 }}
          pointerEvents="none"
        />
      </View>

      {/* Copy */}
      <View style={{ flex: 1, paddingHorizontal: 28, paddingTop: 4, gap: 12 }}>
        <AppText variant="label" color={item.accent}>
          {item.eyebrow}
        </AppText>
        <AppText variant="display">{item.title}</AppText>
        <AppText variant="body">{item.subtitle}</AppText>
      </View>
    </View>
  );
}

function Dot({
  i,
  scrollX,
  width,
  accent,
}: {
  i: number;
  scrollX: SharedValue<number>;
  width: number;
  accent: string;
}) {
  const style = useAnimatedStyle(() => {
    const input = [(i - 1) * width, i * width, (i + 1) * width];
    return {
      width: interpolate(scrollX.value, input, [7, 22, 7], Extrapolation.CLAMP),
      opacity: interpolate(scrollX.value, input, [0.25, 1, 0.25], Extrapolation.CLAMP),
    };
  });
  return <Animated.View style={[styles.dot, { backgroundColor: accent }, style]} />;
}

const styles = StyleSheet.create({
  controls: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingTop: 20,
    paddingHorizontal: 24,
    gap: 20,
  },
  dots: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center' },
  dot: { height: 7, borderRadius: 4, marginHorizontal: 3 },
  cta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 16,
    borderRadius: 16,
  },
});
