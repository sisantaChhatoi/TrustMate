import { Ionicons } from '@expo/vector-icons';
import { View } from 'react-native';

import { space } from '@/constants/design';
import { AppText } from './app-text';
import { IconBadge } from './icon-badge';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

/**
 * Icon + (title / description) laid out horizontally. The badge aligns to the
 * top of the text block so multi-line descriptions stay tidy.
 */
export function FeatureRow({
  icon,
  title,
  description,
}: {
  icon: IconName;
  title: string;
  description: string;
}) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: space.md }}>
      <IconBadge name={icon} tone="brand" size="md" />
      <View style={{ flex: 1, gap: 2, paddingTop: 2 }}>
        <AppText variant="subtitle">{title}</AppText>
        <AppText variant="caption">{description}</AppText>
      </View>
    </View>
  );
}
