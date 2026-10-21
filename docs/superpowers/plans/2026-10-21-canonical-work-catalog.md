# Canonical Work Catalog Expansion

**Goal:** Expand the four-work production catalog with source-linked public-domain
metadata without changing existing IDs, curated names or performance programs.

**Architecture:** The approved full-service delivery unit 3 uses a local catalog,
not LLM-generated music facts. Open Opus is suitable but its API connection times
out today. Use Wikidata's official query service and the existing reviewed
220-composer identity registry. Import only single-composer musical-work concepts;
retain other types/conflicts in the snapshot/report, not as verified works.

**Execution:** Sequential in this thread per user instructions; TDD. No paid LLM,
no new cloud service, no schema changes or changes to other Supabase projects.

## Steps

- [x] Write failing tests in `workers/tests/test_work_catalog.py` for composer
  identity reuse, excluded types, opus/catalogue interpretation, duplicate-safe
  IDs, source provenance, curated-record preservation and dry-run behavior.
- [x] Implement `workers/src/classic_hubble_pipeline/work_catalog.py` and
  `catalog_import.py`: query in bounded sequential batches with local caching,
  explicit timeouts and no retries on provider errors; validate the whole snapshot
  before writes; persist deterministic-ID rows with ignore-duplicates and retain
  source snapshots/crosswalks in private provider records. No deletes.
- [x] Add regression tests for partial catalogue numbers and imported candidates
  requiring review. Preserve current curated matches. Importing a reference work
  must never publish a concert program or send notifications.
- [x] Collect all eligible records for the 220 known composer IDs. Dry-run and
  inspect source anomalies/merges before applying. Keep the data readable past
  1,000 rows. Post-import response size/speed is recorded in `docs/work-catalog.md`.
- [x] Verify actual database counts, preserved four IDs/19 aliases, repeat-import
  idempotence, representative matches and review-only behavior. Run Python/web
  suites, lint and build. Document coverage and source/license limitations.
- [x] Commit only this unit's files, push a PR, verify CI, merge and verify the
  production deployment. Leave user-owned `docs/capstone/` unchanged.

## Accuracy Contract

The database enforces valid IDs; this is not a guarantee that the selected music
is correct. OCR errors, missing works, alternate catalog editions, arrangements,
movements and ambiguous composers require abstention. New imported works remain
review candidates until curated. LLM extraction must remain grounded in OCR spans.
