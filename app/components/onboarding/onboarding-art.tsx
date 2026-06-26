import { Ionicons } from '@expo/vector-icons';
import { useEffect } from 'react';
import { View, ViewStyle } from 'react-native';
import Animated, {
  Easing,
  interpolate,
  useAnimatedProps,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import Svg, {
  Circle,
  Defs,
  Line,
  LinearGradient as SvgGradient,
  Path,
  Rect,
  Stop,
} from 'react-native-svg';

const ACircle = Animated.createAnimatedComponent(Circle);
const ALine = Animated.createAnimatedComponent(Line);
const ARect = Animated.createAnimatedComponent(Rect);

// Cohesive graphics palette (used on a LIGHT background).
const C = {
  indigo: '#4F46E5',
  indigoSoft: 'rgba(79,70,229,0.12)',
  violet: '#7C3AED',
  violetSoft: 'rgba(124,58,237,0.12)',
  teal: '#0D9488',
  tealSoft: 'rgba(13,148,136,0.14)',
  sky: '#0EA5E9',
  amber: '#F59E0B',
  red: '#EF4444',
  redSoft: 'rgba(239,68,68,0.12)',
  line: '#CBD5E1',
  ink: '#334155',
};

const canvas = (w: number, h: number): ViewStyle => ({ width: w, height: h, alignItems: 'center', justifyContent: 'center' });

// ── shared motion helpers ──────────────────────────────────────────────────

function PulseRing({ size, color, delay = 0 }: { size: number; color: string; delay?: number }) {
  const p = useSharedValue(0);
  useEffect(() => {
    p.value = withDelay(delay, withRepeat(withTiming(1, { duration: 2400, easing: Easing.out(Easing.quad) }), -1, false));
  }, [p, delay]);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: 0.5 + p.value }], opacity: (1 - p.value) * 0.6 }));
  return (
    <Animated.View
      pointerEvents="none"
      style={[{ position: 'absolute', width: size, height: size, borderRadius: size / 2, borderWidth: 2, borderColor: color }, style]}
    />
  );
}

function Float({ children, amplitude = 7 }: { children: React.ReactNode; amplitude?: number }) {
  const f = useSharedValue(0);
  useEffect(() => {
    f.value = withRepeat(withTiming(1, { duration: 2600, easing: Easing.inOut(Easing.quad) }), -1, true);
  }, [f]);
  const style = useAnimatedStyle(() => ({ transform: [{ translateY: -amplitude * f.value }] }));
  return <Animated.View style={style}>{children}</Animated.View>;
}

/** A dot that travels in a straight line between two points, looping. */
function Packet({
  from,
  to,
  color,
  size = 10,
  delay = 0,
  duration = 1400,
  interceptAt,
}: {
  from: { x: number; y: number };
  to: { x: number; y: number };
  color: string;
  size?: number;
  delay?: number;
  duration?: number;
  interceptAt?: number; // 0..1 — fade out (blocked) at this progress instead of reaching `to`
}) {
  const p = useSharedValue(0);
  useEffect(() => {
    p.value = withDelay(delay, withRepeat(withTiming(1, { duration, easing: Easing.inOut(Easing.quad) }), -1, false));
  }, [p, delay, duration]);
  const style = useAnimatedStyle(() => {
    const end = interceptAt ?? 1;
    const prog = Math.min(p.value, end);
    const fade = interceptAt
      ? interpolate(p.value, [0, end * 0.6, end], [0, 1, 0])
      : interpolate(p.value, [0, 0.15, 0.85, 1], [0, 1, 1, 0]);
    return {
      opacity: fade,
      transform: [
        { translateX: from.x + (to.x - from.x) * prog - size / 2 },
        { translateY: from.y + (to.y - from.y) * prog - size / 2 },
      ],
    };
  });
  return <Animated.View style={[{ position: 'absolute', width: size, height: size, borderRadius: size / 2, backgroundColor: color }, style]} />;
}

/** Circular node with an icon, used as an absolute-positioned overlay. */
function Node({
  x,
  y,
  d,
  bg,
  icon,
  iconColor,
  border,
}: {
  x: number;
  y: number;
  d: number;
  bg: string;
  icon: React.ComponentProps<typeof Ionicons>['name'];
  iconColor: string;
  border?: string;
}) {
  return (
    <View
      style={{
        position: 'absolute',
        left: x - d / 2,
        top: y - d / 2,
        width: d,
        height: d,
        borderRadius: d / 2,
        backgroundColor: bg,
        borderWidth: border ? 1.5 : 0,
        borderColor: border,
        alignItems: 'center',
        justifyContent: 'center',
      }}>
      <Ionicons name={icon} size={d * 0.46} color={iconColor} />
    </View>
  );
}

// ── Slide 1: call protection — scammer → agent intercepts → caller ─────────

export function CallFlowArt() {
  const caller = { x: 50, y: 168 };
  const agent = { x: 150, y: 70 };
  const scammer = { x: 250, y: 168 };
  return (
    <View style={canvas(300, 240)}>
      <Svg width={300} height={240} style={{ position: 'absolute' }}>
        <Line x1={scammer.x} y1={scammer.y} x2={agent.x} y2={agent.y} stroke={C.line} strokeWidth={2} strokeDasharray="5 6" />
        <Line x1={agent.x} y1={agent.y} x2={caller.x} y2={caller.y} stroke={C.line} strokeWidth={2} strokeDasharray="5 6" />
      </Svg>

      {/* scammer attempts get intercepted at the agent */}
      <Packet from={scammer} to={agent} color={C.red} delay={0} interceptAt={0.78} />
      <Packet from={scammer} to={agent} color={C.red} delay={700} interceptAt={0.78} />
      {/* protected line stays open agent → caller */}
      <Packet from={agent} to={caller} color={C.teal} delay={300} size={8} />
      <Packet from={agent} to={caller} color={C.teal} delay={1000} size={8} />

      <Node x={scammer.x} y={scammer.y} d={50} bg={C.redSoft} icon="warning" iconColor={C.red} border="rgba(239,68,68,0.3)" />
      <Node x={caller.x} y={caller.y} d={50} bg="rgba(14,165,233,0.12)" icon="call" iconColor={C.sky} border="rgba(14,165,233,0.3)" />

      {/* agent (you) — emphasised */}
      <PulseRing size={92} color="rgba(79,70,229,0.4)" />
      <View style={{ position: 'absolute', left: agent.x - 33, top: agent.y - 33 }}>
        <Float amplitude={5}>
          <View style={{ width: 66, height: 66, borderRadius: 33, backgroundColor: C.indigo, alignItems: 'center', justifyContent: 'center' }}>
            <Ionicons name="shield-checkmark" size={32} color="#FFFFFF" />
          </View>
        </Float>
      </View>
    </View>
  );
}

// ── Slide 2: chat risk checks — knowledge graph ────────────────────────────

const HUB = { x: 150, y: 120 };
const GNODES = [
  { x: 64, y: 56, c: C.teal },
  { x: 158, y: 40, c: C.violet },
  { x: 244, y: 78, c: C.amber },
  { x: 250, y: 168, c: C.indigo },
  { x: 168, y: 206, c: C.teal },
  { x: 70, y: 196, c: C.violet },
  { x: 40, y: 124, c: C.indigo },
];

function GraphNode({ x, y, c, delay }: { x: number; y: number; c: string; delay: number }) {
  const s = useSharedValue(0);
  useEffect(() => {
    s.value = withDelay(delay, withTiming(1, { duration: 480, easing: Easing.out(Easing.back(1.6)) }));
  }, [s, delay]);
  const props = useAnimatedProps(() => ({ r: 9 * s.value, opacity: s.value }));
  return <ACircle cx={x} cy={y} fill={c} animatedProps={props} />;
}

function GraphEdge({ a, b, delay }: { a: { x: number; y: number }; b: { x: number; y: number }; delay: number }) {
  const len = Math.hypot(b.x - a.x, b.y - a.y);
  const d = useSharedValue(1);
  useEffect(() => {
    d.value = withDelay(delay, withTiming(0, { duration: 600, easing: Easing.out(Easing.cubic) }));
  }, [d, delay]);
  const props = useAnimatedProps(() => ({ strokeDashoffset: len * d.value }));
  return (
    <ALine
      x1={a.x}
      y1={a.y}
      x2={b.x}
      y2={b.y}
      stroke="rgba(124,58,237,0.35)"
      strokeWidth={2}
      strokeDasharray={len}
      animatedProps={props}
    />
  );
}

export function GraphArt() {
  return (
    <View style={canvas(300, 240)}>
      <Svg width={300} height={240} style={{ position: 'absolute' }}>
        {GNODES.map((n, i) => (
          <GraphEdge key={`e${i}`} a={HUB} b={n} delay={300 + i * 90} />
        ))}
        {/* a couple of cross links for a richer mesh */}
        <GraphEdge a={GNODES[0]} b={GNODES[1]} delay={900} />
        <GraphEdge a={GNODES[3]} b={GNODES[4]} delay={1000} />
        {GNODES.map((n, i) => (
          <GraphNode key={`n${i}`} x={n.x} y={n.y} c={n.c} delay={500 + i * 90} />
        ))}
      </Svg>

      {/* intelligence pulses flowing out of the hub */}
      {GNODES.map((n, i) => (
        <Packet key={`p${i}`} from={HUB} to={n} color={n.c} size={7} delay={1200 + i * 160} duration={1500} />
      ))}

      <PulseRing size={86} color="rgba(124,58,237,0.4)" />
      <View style={{ position: 'absolute', left: HUB.x - 26, top: HUB.y - 26 }}>
        <View style={{ width: 52, height: 52, borderRadius: 26, backgroundColor: C.violet, alignItems: 'center', justifyContent: 'center' }}>
          <Ionicons name="git-network" size={26} color="#FFFFFF" />
        </View>
      </View>
    </View>
  );
}

// ── Slide 3: geospatial intelligence — India map with hotspots ─────────────

const INDIA =
  'M64 20 L82 30 L100 24 L120 32 L138 26 L150 40 L146 52 L162 60 L150 68 L136 60 L132 76 ' +
  'L124 96 L122 118 L116 140 L108 162 L96 190 L88 208 L82 186 L78 160 L72 134 L66 116 ' +
  'L52 104 L40 98 L50 84 L48 66 L58 46 Z';

const HOTSPOTS = [
  { x: 84, y: 56, c: C.red, delay: 0 }, // Delhi
  { x: 62, y: 116, c: C.amber, delay: 500 }, // Mumbai
  { x: 132, y: 86, c: C.red, delay: 900 }, // Kolkata
  { x: 96, y: 126, c: C.amber, delay: 300 }, // Hyderabad
  { x: 88, y: 156, c: C.red, delay: 1200 }, // Bengaluru
];

function Hotspot({ x, y, c, delay }: { x: number; y: number; c: string; delay: number }) {
  const p = useSharedValue(0);
  useEffect(() => {
    p.value = withDelay(delay, withRepeat(withTiming(1, { duration: 1900, easing: Easing.out(Easing.quad) }), -1, false));
  }, [p, delay]);
  const ring = useAnimatedProps(() => ({ r: 4 + p.value * 16, opacity: 1 - p.value }));
  return (
    <>
      <ACircle cx={x} cy={y} stroke={c} strokeWidth={2} fill="none" animatedProps={ring} />
      <Circle cx={x} cy={y} r={4} fill={c} />
    </>
  );
}

export function MapArt() {
  return (
    <View style={canvas(220, 240)}>
      <Float amplitude={5}>
        <Svg width={200} height={230} viewBox="0 0 200 230">
          <Path d={INDIA} fill={C.tealSoft} stroke={C.teal} strokeWidth={2} strokeLinejoin="round" />
          {/* faint links between hotspots — the crime network */}
          <Line x1={84} y1={56} x2={62} y2={116} stroke="rgba(239,68,68,0.25)" strokeWidth={1.5} strokeDasharray="3 5" />
          <Line x1={62} y1={116} x2={96} y2={126} stroke="rgba(239,68,68,0.25)" strokeWidth={1.5} strokeDasharray="3 5" />
          <Line x1={96} y1={126} x2={132} y2={86} stroke="rgba(239,68,68,0.25)" strokeWidth={1.5} strokeDasharray="3 5" />
          <Line x1={96} y1={126} x2={88} y2={156} stroke="rgba(239,68,68,0.25)" strokeWidth={1.5} strokeDasharray="3 5" />
          {HOTSPOTS.map((h, i) => (
            <Hotspot key={i} x={h.x} y={h.y} c={h.c} delay={h.delay} />
          ))}
        </Svg>
      </Float>
    </View>
  );
}

// ── Slide 4: always evolving — radar sweep ─────────────────────────────────

function Blip({ x, y, c, delay }: { x: number; y: number; c: string; delay: number }) {
  const p = useSharedValue(0);
  useEffect(() => {
    p.value = withDelay(
      delay,
      withRepeat(withSequence(withTiming(1, { duration: 500 }), withTiming(0, { duration: 1400 })), -1, false),
    );
  }, [p, delay]);
  const props = useAnimatedProps(() => ({ r: 3 + p.value * 3, opacity: p.value }));
  return <ACircle cx={x} cy={y} fill={c} animatedProps={props} />;
}

export function RadarArt() {
  const rot = useSharedValue(0);
  useEffect(() => {
    rot.value = withRepeat(withTiming(1, { duration: 3600, easing: Easing.linear }), -1, false);
  }, [rot]);
  const sweep = useAnimatedStyle(() => ({ transform: [{ rotate: `${rot.value * 360}deg` }] }));

  return (
    <View style={canvas(240, 240)}>
      <Svg width={240} height={240} style={{ position: 'absolute' }}>
        <Circle cx={120} cy={120} r={100} stroke="rgba(79,70,229,0.18)" strokeWidth={1.5} fill="none" />
        <Circle cx={120} cy={120} r={68} stroke="rgba(79,70,229,0.22)" strokeWidth={1.5} fill="none" />
        <Circle cx={120} cy={120} r={36} stroke="rgba(79,70,229,0.28)" strokeWidth={1.5} fill="none" />
        <Line x1={20} y1={120} x2={220} y2={120} stroke="rgba(79,70,229,0.15)" strokeWidth={1} />
        <Line x1={120} y1={20} x2={120} y2={220} stroke="rgba(79,70,229,0.15)" strokeWidth={1} />
        <Blip x={166} y={84} c={C.amber} delay={200} />
        <Blip x={84} y={72} c={C.red} delay={1100} />
        <Blip x={72} y={158} c={C.amber} delay={700} />
        <Blip x={168} y={156} c={C.teal} delay={1700} />
        <Blip x={150} y={120} c={C.red} delay={2300} />
      </Svg>

      {/* rotating sweep wedge */}
      <Animated.View style={[{ position: 'absolute', width: 240, height: 240 }, sweep]}>
        <Svg width={240} height={240}>
          <Defs>
            <SvgGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
              <Stop offset="0" stopColor={C.teal} stopOpacity={0.45} />
              <Stop offset="1" stopColor={C.teal} stopOpacity={0} />
            </SvgGradient>
          </Defs>
          <Path d="M120 120 L120 20 A100 100 0 0 1 206 70 Z" fill="url(#sweep)" />
        </Svg>
      </Animated.View>

      <View style={{ position: 'absolute', width: 16, height: 16, borderRadius: 8, backgroundColor: C.indigo }} />
    </View>
  );
}
