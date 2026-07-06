// Dev-only flags for live debugging. Flip off to restore normal behaviour.
export const flags = {
  // Skip auth routing after onboarding → always open the signup form, and make
  // the submit a no-op, so the form can be tweaked without hitting the backend.
  debugSignupForm: false,
  // Same, but opens the login form instead. Takes precedence over signup.
  debugLoginForm: false,
  // Show the test-notification card on the home screen.
  showTestNotify: false,
};
