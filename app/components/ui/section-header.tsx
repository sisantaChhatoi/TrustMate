import { View } from 'react-native';

import { space } from '@/constants/design';
import { AppText } from './app-text';

/** Eyebrow label + title (+ optional description). Keeps section intros uniform. */
export function SectionHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
}) {
  return (
    <View style={{ gap: space.xs }}>
      {eyebrow ? <AppText variant="label">{eyebrow}</AppText> : null}
      <AppText variant="title">{title}</AppText>
      {description ? <AppText variant="body">{description}</AppText> : null}
    </View>
  );
}
