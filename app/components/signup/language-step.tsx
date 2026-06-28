import { View } from 'react-native';

import { AppText } from '@/components/ui/app-text';
import { ChipSelect } from '@/components/ui/chip-select';
import { INDIAN_LANGUAGES } from '@/constants/app';
import { colors, space } from '@/constants/design';
import { SignupErrors } from './types';

export function LanguageStep({
  languages,
  setLanguages,
  errors,
}: {
  languages: string[];
  setLanguages: (next: string[]) => void;
  errors: SignupErrors;
}) {
  return (
    <View style={{ gap: space.md }}>
      <ChipSelect options={INDIAN_LANGUAGES} value={languages} onChange={setLanguages} max={3} />
      {errors.languages ? (
        <AppText variant="caption" color={colors.danger}>
          {errors.languages}
        </AppText>
      ) : null}
    </View>
  );
}
