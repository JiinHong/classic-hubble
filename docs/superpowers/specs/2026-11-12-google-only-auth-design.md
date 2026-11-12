# Google-only sign-in for Classic Hubble

Decision: replace email/password with Google through the existing Supabase Auth project. Keep public search and work/concert pages anonymous. No new account database, login landing page, or access to YouTube data.

## User flow

- The header login button and the login actions on work/watchlist pages start Google sign-in directly. Suppress duplicate starts. Never request YouTube or offline-access scopes.
- Keep the existing browser Supabase client, session listener and sign-out flow. Use PKCE and one app callback at /auth/callback. Exactly one code-exchange owner (SDK detection or explicit exchange, never both).
- Store only the originating internal path and search parameters in this tab's session storage. Validate the parsed destination against the current origin before restoring it. Reject an external origin, a protocol-relative URL or the callback itself. Default to / if storage is unavailable. Strip credentials and OAuth parameters from navigation and logs.
- On success, replace the callback history entry with the saved destination and reload the existing user's library. On cancellation/failure, return there with a short retryable message; never silently start another sign-in or mutate an interest on the user's behalf.
- Keep the original user UUID as the owner of watched works and notification preferences. Do not merge accounts or reassign rows by matching email in the application.

## Production rollout

1. Configure a Web application in Google Auth Platform. Use https://classichubble.com as a JavaScript origin and https://klnfamtwxwrelrjeguqb.supabase.co/auth/v1/callback as the Google redirect URI. Enter the ID and secret directly in the Google provider for this Supabase project. Never log or commit secrets.
2. Allow the exact app callback https://classichubble.com/auth/callback in Supabase redirect URLs. For testing use explicitly listed, trusted origins, not arbitrary previews. Keep the email provider and the existing production UI available until ready.
3. Validate the Google flow on an allow-listed test URL before releasing the new UI. Test the production domain before retiring email. A redirect to Google or an enabled-provider flag alone is not a successful login.
4. With an owner-controlled, confirmed email account and the same verified Google email, compare the Supabase user UUID, watched works and notification preferences before and after sign-in. Also test a new account, session persistence and sign-out. Never include personal identifiers, OAuth tokens or passwords in test output.
5. Before removing the old login entry point or disabling email, establish whether existing email-only users lack a viable Google login. If any do, keep the existing production access available until they have a verified migration path. Do not enable manual linking or import account data as part of this change. If there are no existing email users, document that instead of claiming a migration.
6. After verification, expose only Google in the production UI and disable the email provider. Verify Google sign-in still works and email/password is no longer accepted. On rollout failure restore the previous UI and email provider; do not delete users, identities or saved works.

## Acceptance checks

- Public search remains available without an account. The header, watchlist and signed-out work actions start only Google OAuth in the new UI.
- Preserve query parameters on return (e.g. /?q=Beethoven); preserve work/watchlist routes. Browser back does not replay the callback.
- Cover missing or expired credentials, denied consent, duplicate requests/callbacks, unsafe return locations, missing storage and retry.
- Verify existing account identity and content, authenticated library isolation, page refresh, and sign-out. Unit tests with mocked OAuth do not substitute for the real production sign-in check.

References: [Supabase Google setup](https://supabase.com/docs/guides/auth/social-sign-in/auth-google), [identity linking](https://supabase.com/docs/guides/auth/auth-identity-linking).
