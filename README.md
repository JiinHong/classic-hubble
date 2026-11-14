# Classic Hubble

Classic Hubble is a work-based classical concert discovery MVP. It helps users search by composition, inspect upcoming performances, save favorite works, and receive alerts when a watched work appears in a program.

## Apps

- `apps/web`: Next.js web MVP with search, work pages, performance pages, watchlist, and admin review queue.
- `packages/shared`: Seed data, types, and matching helpers shared by the web app.
- `workers`: Python data pipeline for KOPIS sync, poster OCR extraction, work normalization, and notification jobs.
- `supabase`: Supabase/Postgres schema draft.

## Local Setup

```bash
pnpm install
pnpm dev
```

Copy `.env.example` to `.env.local` inside `apps/web` or export the variables in your shell when connecting real services.

The local web app is already configured for the Classic Hubble Supabase project in
`apps/web/.env.local` using the project URL and publishable key.

## Verification

```bash
pnpm --filter @classic-hubble/shared test
pnpm --filter web test
pnpm --filter web lint
.venv/bin/python -m pytest workers/tests
pnpm --filter web build
```

## Automation

GitHub Actions runs the full web and worker verification suite on pushes and pull
requests. The catalog ingestion workflow runs every day at 16:27 Asia/Seoul,
after the documented 15:00 KOPIS refresh.

The scheduled run refreshes the KOPIS catalog from seven days in the past through
180 days in the future. Official venue enrichment then checks today through 31 days ahead.
NOL requests are paused; existing NOL evidence remains intact. The workflow requires `KOPIS_API_KEY`, `SUPABASE_URL`, and
`SUPABASE_SECRET_KEY` as GitHub Actions repository secrets.

## Architecture Notes

- Supabase Auth is the default login layer. Anonymous browsing can stay open, while watchlists and notifications require a user.
- The web app uses Supabase Google sign-in and per-user watchlists. The watchlist does not change existing email preferences.
- KOPIS supplies nationwide classical performance/facility records. Official enrichment binds a single event date, time and hall to a published programme: SAC calendar and detail, Sejong's KOPIS-linked detail, or Bucheon Philharmonic's event and separately numbered programme notes. Seoul Philharmonic discovery observes its robots restrictions and reports a policy hold when disallowed. No OCR or paid model is called here.
- Only unambiguous printed composer, title and catalogue matches create public links. A partial list is not the entire concert programme. Conflicting existing sources and changed programmes are preserved for reconciliation. Run `python -m classic_hubble_pipeline.official_program_sync --start YYYY-MM-DD --end YYYY-MM-DD` to preview; add `--apply` to publish, or repeat `--kopis PF...` for selected events.
- The `kopis-sync` worker stores raw KOPIS and NOL records first, then idempotently upserts facilities, halls, performances, NOL-owned program rows, and detail images.
- KOPIS list requests are split into at most 31-day windows and 100-row pages; provider failures are retried and API result codes remain distinguishable from transport errors.
- OCR/LLM matches below the confidence threshold should be routed to the admin review queue.
- Email and web push share the same watchlist matching logic, then diverge only at delivery.
- Concert alert eligibility is email-only. The email delivery integration is not yet implemented.

## Supabase

- Project ref: `klnfamtwxwrelrjeguqb`
- API URL: `https://klnfamtwxwrelrjeguqb.supabase.co`
- Applied migrations:
  - `initial_classic_hubble_schema`
  - `harden_rls_and_indexes`
  - `revoke_public_rls_auto_enable`
  - `add_performance_artists`
  - `seed_catalog_sample`
  - `kopis_ingestion_schema`
  - `add_provider_records_service_policy`
  - `add_nol_program_enrichment`

Security advisors are clean after the migrations. Performance advisors may report unused indexes on a fresh database until traffic or seed data exercises them.
