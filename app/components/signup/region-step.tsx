import { View } from 'react-native';

import { TextField } from '@/components/ui/text-field';
import { space } from '@/constants/design';
import { SignupErrors } from './types';

export function RegionStep({
  accent,
  age,
  setAge,
  state,
  setState,
  city,
  setCity,
  pin,
  setPin,
  errors,
}: {
  accent: string;
  age: string;
  setAge: (v: string) => void;
  state: string;
  setState: (v: string) => void;
  city: string;
  setCity: (v: string) => void;
  pin: string;
  setPin: (v: string) => void;
  errors: SignupErrors;
}) {
  return (
    <View style={{ gap: space.lg }}>
      <View style={{ flexDirection: 'row', gap: space.md }}>
        <View style={{ flex: 1 }}>
          <TextField
            label="State"
            placeholder="e.g. Karnataka"
            accent={accent}
            value={state}
            onChangeText={setState}
            error={errors.state}
          />
        </View>
        <View style={{ flex: 1 }}>
          <TextField
            label="City"
            placeholder="e.g. Bengaluru"
            accent={accent}
            value={city}
            onChangeText={setCity}
            error={errors.city}
          />
        </View>
      </View>
      <View style={{ flexDirection: 'row', gap: space.md }}>
        <View style={{ width: 110 }}>
          <TextField
            label="Age"
            placeholder="Age"
            keyboardType="number-pad"
            maxLength={3}
            accent={accent}
            value={age}
            onChangeText={setAge}
            error={errors.age}
          />
        </View>
        <View style={{ flex: 1 }}>
          <TextField
            label="PIN code"
            icon="location-outline"
            placeholder="6-digit area PIN"
            keyboardType="number-pad"
            maxLength={6}
            accent={accent}
            value={pin}
            onChangeText={setPin}
            error={errors.pin}
          />
        </View>
      </View>
    </View>
  );
}
