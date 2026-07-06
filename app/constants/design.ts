// ──────────────────────────────────────────────────────────────────────────
// Design system tokens. Single source of truth for the app's look & feel.
// Principle: text stays near-monochrome (ink scale). Color is reserved for
// icons, primary actions, and the danger state — never decorative.
// ──────────────────────────────────────────────────────────────────────────

export const colors = {
  // Brand — cyber blue. Primary actions, key icons, links.
  brand: '#2563EB',
  brandDark: '#1D4ED8',
  brandTint: '#EFF6FF',
  brandBorder: '#BFDBFE',

  // Ink scale — slate undertone to harmonise with the blue palette.
  ink: '#0F172A',
  body: '#334155',
  muted: '#64748B',
  faint: '#94A3B8',

  // Surfaces — sky-blue-tinted background, white cards.
  bg: '#F0F7FF',
  surface: '#FFFFFF',
  surfaceAlt: '#EFF6FF',
  border: '#DBEAFE',
  borderStrong: '#BFDBFE',

  // Semantic — used sparingly, only where it carries meaning.
  danger: '#DC2626',
  dangerTint: '#FEF2F2',
  dangerBorder: '#FECACA',
  success: '#059669',
  successTint: '#ECFDF5',

  teal: '#0D9488',
  tealTint: '#CCFBF1',
  tealBorder: '#99F6E4',

  amber: '#D97706',
  amberTint: '#FEF3C7',
  amberBorder: '#FDE68A',

  white: '#FFFFFF',
} as const;

// Spacing scale (4-pt grid). Reference everywhere instead of magic numbers.
export const space = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  huge: 40,
} as const;

export const radius = {
  sm: 10,
  md: 14,
  lg: 18,
  xl: 24,
  pill: 999,
} as const;

// Type scale. weight values are RN-accepted strings.
export const typography = {
  display: {
    fontSize: 30,
    fontWeight: '800',
    lineHeight: 36,
    letterSpacing: -0.5,
    color: colors.ink,
  },
  title: {
    fontSize: 24,
    fontWeight: '800',
    lineHeight: 30,
    letterSpacing: -0.3,
    color: colors.ink,
  },
  heading: { fontSize: 18, fontWeight: '700', lineHeight: 24, color: colors.ink },
  subtitle: { fontSize: 16, fontWeight: '600', lineHeight: 22, color: colors.ink },
  body: { fontSize: 15, fontWeight: '400', lineHeight: 22, color: colors.body },
  bodyStrong: { fontSize: 15, fontWeight: '600', lineHeight: 22, color: colors.ink },
  caption: { fontSize: 13, fontWeight: '400', lineHeight: 19, color: colors.muted },
  label: {
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 16,
    letterSpacing: 0.8,
    color: colors.muted,
    textTransform: 'uppercase',
  },
  link: { fontSize: 14, fontWeight: '700', lineHeight: 20, color: colors.brand },
} as const;

export const shadow = {
  card: {
    shadowColor: '#1B1B2F',
    shadowOpacity: 0.05,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 2,
  },
} as const;

export type TypeVariant = keyof typeof typography;
