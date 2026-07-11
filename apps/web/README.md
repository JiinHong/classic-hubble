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
- `/watchlist`: saved works and notification channels.
- `/admin/review`: OCR review queue.

The catalog reads from the Classic Hubble Supabase project and falls back to
`@classic-hubble/shared` seed data if Supabase is unavailable. Supabase Auth handles
email/password sessions, and signed-in users can persist watched works and email
notification preferences. Web push remains disabled in the UI until VAPID keys and
browser subscription registration are configured.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
