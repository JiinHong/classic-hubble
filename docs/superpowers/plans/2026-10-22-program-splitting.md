# Program Splitting Implementation Plan

> **For agentic workers:** Execute inline with superpowers:executing-plans; the user requested implementation and production application.

**Goal:** Resolve the 135 complex NOL blocks and nine no-candidate observations without inventing work identities or losing source text.

**Architecture:** A deterministic segmenter separates composer/work headings from translations, movements, credits and notices. The existing matcher resolves each segment against a provenance-backed catalogue. An atomic, service-role-only database function replaces NOL rows after comparing the original snapshot, and archives the previous rows in existing provider records.

**Tech Stack:** Python, pytest, httpx, PostgreSQL/Supabase, GitHub Actions, Next.js/Vercel.

## Global Constraints
- No paid LLM calls or new image processing in this repair.
- Preserve all original source text, explicit excerpt/arrangement scope, and existing linked/non-NOL rows.
- Do not infer a composer's identity from a generic work title, erase conflicting catalogue numbers, or combine different dates.
- Catalogue additions need cited identity evidence; "no candidate" is not equivalent to a missing work.
- Production project must be `klnfamtwxwrelrjeguqb`.

## Tasks
- [x] Freeze production rows/catalogue and inspect all 144 requested observations.
- [x] Add failing segmentation tests in `workers/tests/test_program_split.py`; run pytest and confirm failure before implementing `split_program_block(item, matcher)` in `workers/src/classic_hubble_pipeline/program_split.py`.
- [x] Add tests for Mozart alternate catalogue numbers and annotation handling; improve matching without weakening conflict checks.
- [x] Add a sourced repair manifest for the nine no-candidate cases; test every identity and apply additive changes with original-value checks.
- [x] Add failing repository/backfill tests, then atomic NOL replacement and integration into `_map_nol_program_items`; verify stale-snapshot rejection, source preservation and idempotence.
- [x] Replay every frozen input, inspect all proposals, apply to production, and read back all rows. Record unresolved cases accurately.
- [ ] Run full worker tests, lint, regression replay and CI; commit, merge and verify deployment.

## Verification Commands
```sh
.venv/bin/python -m pytest workers/tests/test_program_split.py workers/tests/test_program_matching.py workers/tests/test_music_matching.py -q
.venv/bin/python -m pytest workers/tests -q
```

Production writes require a successful dry run, an archived intent, and a per-performance compare-and-swap. All reports remain in the private task artifact directory.

## Production Result (2026-10-22)
- Examined all 135 complex blocks and nine no-candidate observations. The complex blocks became 215 segments: 33 blocks split into 113 segments, while 102 stayed together because translations or movements must not become separate works.
- Applied 49 performance replacements. NOL rows increased from 224 to 304; linked rows increased from 33 to 101 (68 new links). Preserved all original IDs, timestamps, source content, previous links and five other-provider rows.
- Resolved all nine original no-candidate observations through three sourced work additions, four catalogue corrections and 19 aliases. See `workers/data/program-catalog-repairs.json` for identity evidence.
- The targeted inputs still contain 156 unlinked segments: 77 composer-unconfirmed, 71 no-candidate, two ambiguous, three non-program, one multiple-program-dates, one uncertain-source-title and one orphan-movements. These are diagnostic outcomes, not proof that 71 works are missing from the database.
- Production checks: stale snapshots rejected, invalid foreign keys rolled back, identical writes preserved IDs, and a second planner pass generated zero repairs. Anonymous and authenticated users cannot execute the write function; only the service role can.
- No LLM calls were made. The affected performances are past events, so this repair does not resolve future-performance collection coverage.
- Local verification: 639 worker tests, 19 shared tests, 180 web tests, ESLint and the Next.js production build passed.

## Deployment Order
1. Apply `20261022074017_atomic_nol_program_replacement.sql` before deploying the collector. This was applied and verified in the correct production project before the backfill.
2. Deploy the matching/collector code through GitHub main and the web component relationship through Vercel.
3. Check the production performance display and the new component-to-parent link.
