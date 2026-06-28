import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { StyleSheet, View } from 'react-native';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

// A faint contextual icon plus a soft accent wash — fills the space without
// the noise of decorative blobs.
export function FormBackdrop({ accent, icon }: { accent: string; icon: IconName }) {
  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <LinearGradient
        colors={[accent, 'transparent']}
        style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 280, opacity: 0.09 }}
      />
      <Ionicons
        name={icon}
        size={300}
        color={accent}
        style={{ position: 'absolute', bottom: -40, right: -70, opacity: 0.05 }}
      />
    </View>
  );
}
