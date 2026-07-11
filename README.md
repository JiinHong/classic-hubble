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
after the documented 15:00 KOPIS refresh and before NOL's common evening ticket
opening window.

The scheduled run refreshes the KOPIS catalog from seven days in the past through
180 days in the future. NOL enrichment is intentionally limited to performances
in the next 31 days while the deterministic adapter's production request volume
is being established. The workflow requires `KOPIS_API_KEY`, `SUPABASE_URL`, and
`SUPABASE_SECRET_KEY` as GitHub Actions repository secrets.

## Architecture Notes

- Supabase Auth is the default login layer. Anonymous browsing can stay open, while watchlists and notifications require a user.
- Email/password login, email-confirmed signup, user watchlists, and email notification preferences are connected to the Classic Hubble Supabase project.
- KOPIS supplies the baseline performance/facility records. The optional deterministic NOL adapter enriches KOPIS-linked goods with text programs or an explicit image-only/not-published state; venue adapters and OCR remain later stages.
- The `kopis-sync` worker stores raw KOPIS and NOL records first, then idempotently upserts facilities, halls, performances, NOL-owned program rows, and detail images.
- KOPIS list requests are split into at most 31-day windows and 100-row pages; provider failures are retried and API result codes remain distinguishable from transport errors.
- OCR/LLM matches below the confidence threshold should be routed to the admin review queue.
- Email and web push share the same watchlist matching logic, then diverge only at delivery.
- Web push delivery endpoints are scaffolded, but the user-facing switch stays disabled until VAPID keys and browser subscription registration are configured.

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
