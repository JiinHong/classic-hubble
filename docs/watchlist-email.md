# Watchlist concert email

Publishing a new trusted performance/work pair inserts one pending email per watcher and performance. The migration baselines existing links; watchlisting an already announced concert does not backfill mail. Republishing a program, adding a second watched work or re-running a dispatcher does not create another delivery. Removing a favorite, disabling email, or closing the concert prevents a pending alert from being claimed. Only the verified address in Supabase Auth can receive mail.

GitHub Actions invokes the production dispatcher after daily ingestion and every 15 minutes. Each run drains up to 30 emails. A scheduler delay delays delivery, not collection. Resend is used only on the server, with the permanent event UUID as its idempotency key. A successful acknowledgement means provider acceptance, not inbox placement. After 23 hours from the first uncertain attempt, automatic retries stop; check Resend before taking further action.

Secrets: keep `RESEND_API_KEY` only in Vercel production. Generate a random 256-bit `WATCHLIST_MAIL_TOKEN`; store it as a sensitive Vercel production variable and a GitHub Actions secret. Store only its SHA-256 digest in `watchmail.worker_key`. No service-role key is required by the web dispatcher. Restart deployment after changing Vercel secrets. Never log tokens or mail contents.

For monitoring, inspect Actions and count pending, accepted or expired events in `watchmail.outbox` using privileged database access. The bearer-authenticated dispatcher accepts an optional single event UUID, never an email address. Test on one consenting account, compare provider acceptance with actual inbox receipt and remove any temporary favorite by its insertion ID.
