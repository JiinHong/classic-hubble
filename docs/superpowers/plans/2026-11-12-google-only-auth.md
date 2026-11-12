# Google-only sign-in implementation plan

Goal: keep public browsing unchanged and replace password entry with a single Google OAuth action. Use the browser Supabase client and a fixed PKCE callback. No production configuration, user-row or library changes in this branch.

- [x] Confirmed the new sign-in and retry expectations failed on the previous implementation. After implementation the focused auth/library suites passed (23 tests).
- [x] Replaced password entry with Google sign-in and a tab-local return destination. The callback owns the PKCE exchange; SDK URL detection is off.
- [x] Verified return-path filtering and storage fallback in unit tests. Tested success, denial and retry, expired code, and missing code in Chrome with synthetic provider responses. Successful sign-in returned to the original filtered search; refresh retained the session and sign-out cleared it. No library writes occurred in these four scenarios.
- [x] Monorepo tests: 304 passed and 8 skipped; web lint and production build passed. A read-only check of the project's public auth settings returned Google disabled, email enabled.

Production acceptance is still pending: no real Google consent, existing-account UUID/watchlist comparison, provider change, or deployment was performed.
