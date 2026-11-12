# Classic Hubble Web

Next.js app for the Classic Hubble MVP.

## Commands

```bash
pnpm dev
pnpm --filter web test
pnpm --filter web lint
pnpm --filter web build
```

## Routes

- `/`: search-first discovery surface.
- `/works/[slug]`: work detail and upcoming performances.
- `/performances/[id]`: performance detail and booking link.
- `/watchlist`: saved works and their upcoming performances.
- `/auth/callback`: completes Google sign-in and returns to the originating page.
- `/admin/review`: OCR review queue.

The catalog reads from the Classic Hubble Supabase project and falls back to
`@classic-hubble/shared` seed data if Supabase is unavailable. This version starts
Google sign-in through Supabase Auth. Signed-in users can persist watched works.
Only email is eligible for concert alerts. Browsing the watchlist does not read
or change existing notification preferences. The eligibility rule alone does not deliver mail.

## Google sign-in

Header and watchlist actions open the same welcome dialog. Only its Google button
starts OAuth; dismissing it leaves the current page and saved works unchanged.
The local Google mark is from the [Google sign-in button assets](https://developers.google.com/identity/branding-guidelines).

Google and Supabase need two different redirect URLs:

- Google Cloud's web OAuth client redirects to `https://klnfamtwxwrelrjeguqb.supabase.co/auth/v1/callback`.
- Supabase Auth must allow the app URL `https://classichubble.com/auth/callback`. To test on a local server, allow its exact callback separately (for example, `http://127.0.0.1:3001/auth/callback`).

Set the Google client ID and secret in the Supabase provider settings, not in the browser or this repository.
Before replacing the production login screen or disabling email, follow the [rollout checklist](../../docs/superpowers/specs/2026-11-12-google-only-auth-design.md) to verify real sign-in and existing users' access to their saved works.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
