# NOL Deterministic Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich KOPIS performances with deterministic NOL program text or an honest publication-status fallback and expose the result in the existing web detail page.

**Architecture:** A focused Python `nol.py` module validates ticket URLs, calls NOL's fixed JSON API host, and converts source payloads into typed program data. `KopisSyncService` invokes that client optionally, stores raw NOL data first, and delegates idempotent normalized writes to `SupabaseRepository`; the Next.js catalog maps the added database fields into the shared performance model.

**Tech Stack:** Python 3.11, httpx, pytest, Supabase Postgres/Data API, TypeScript, React, Next.js, Vitest.

## Global Constraints

- Do not use OCR or LLM interpretation in this increment.
- Accept only official Interpark/NOL ticket hosts and call only `https://api-ticketfront.interpark.com`.
- Preserve successful KOPIS ingestion when optional NOL enrichment fails.
- Store raw provider data before normalized NOL data.
- Replace only NOL-owned program rows during a rerun.

---

### Task 1: NOL URL, parser, and client

**Files:**
- Create: `workers/src/classic_hubble_pipeline/nol.py`
- Create: `workers/tests/test_nol.py`

**Interfaces:**
- Produces: `extract_nol_goods_code(url: str) -> str | None`
- Produces: `parse_nol_payload(goods_code: str, summary: Mapping[str, object], play_db: Mapping[str, object] | None) -> NolPerformanceData`
- Produces: `NolClient.fetch(url: str) -> NolPerformanceData`

- [ ] **Step 1: Write failing tests for official URL validation, Play DB text parsing, detail-HTML fallback, image-only classification, delayed-program language, JSON validation, and retry behavior.**

- [ ] **Step 2: Run `.venv/bin/python -m pytest workers/tests/test_nol.py -q` and verify collection fails because `classic_hubble_pipeline.nol` does not exist.**

- [ ] **Step 3: Implement immutable settings/data classes, an `HTMLParser`-based block and image extractor, conservative composer detection, fixed-host HTTP calls, response validation, and bounded retries.**

- [ ] **Step 4: Run `.venv/bin/python -m pytest workers/tests/test_nol.py -q` and verify all adapter tests pass.**

### Task 2: KOPIS sync integration and Supabase repository

**Files:**
- Modify: `workers/src/classic_hubble_pipeline/kopis_sync.py`
- Modify: `workers/src/classic_hubble_pipeline/supabase.py`
- Modify: `workers/tests/test_kopis_sync.py`
- Modify: `workers/tests/test_supabase.py`

**Interfaces:**
- Consumes: `NolClient.fetch(url) -> NolPerformanceData`
- Produces: `upsert_provider_record(..., provider: str = 'kopis') -> str`
- Produces: `update_performance_program_source(performance_id, payload) -> None`
- Produces: `replace_program_items(performance_id, source_provider, items) -> None`

- [ ] **Step 1: Add failing sync tests proving NOL raw data precedes normalized writes, duplicate goods links are fetched once, and `NolError` increments `nol_errors` without failing KOPIS.**

- [ ] **Step 2: Add failing repository tests for provider selection, performance status patching, provider-scoped deletion, and bulk program insertion.**

- [ ] **Step 3: Run the two test modules and verify failures reference the missing signatures and methods.**

- [ ] **Step 4: Implement optional NOL enrichment after performance upsert, add counters, and implement provider-aware Supabase writes.**

- [ ] **Step 5: Run `.venv/bin/python -m pytest workers/tests/test_kopis_sync.py workers/tests/test_supabase.py -q` and verify both modules pass.**

### Task 3: CLI and database contract

**Files:**
- Modify: `workers/src/classic_hubble_pipeline/cli.py`
- Modify: `workers/tests/test_cli.py`
- Create: `supabase/migrations/20260711143000_add_nol_program_enrichment.sql`
- Modify: `supabase/schema.sql`

**Interfaces:**
- Produces: `classic-hubble-pipeline nol-check --url URL`
- Produces: `classic-hubble-pipeline kopis-sync ... --enrich-nol`

- [ ] **Step 1: Add failing CLI tests for a safe NOL JSON snapshot and opt-in NOL client construction during KOPIS sync.**

- [ ] **Step 2: Run `.venv/bin/python -m pytest workers/tests/test_cli.py -q` and verify the new commands fail.**

- [ ] **Step 3: Implement command routing and dependency injection without requiring KOPIS or Supabase credentials for `nol-check`.**

- [ ] **Step 4: Add the publication-status enum, performance source fields, program-row provenance fields, and provider-position unique index to both migration and canonical schema.**

- [ ] **Step 5: Run all worker tests and verify they pass.**

### Task 4: Web presentation

**Files:**
- Modify: `packages/shared/src/index.ts`
- Modify: `apps/web/src/lib/catalog.ts`
- Modify: `apps/web/src/app/performances/[id]/page.tsx`
- Test: existing web and shared test suites

**Interfaces:**
- Consumes: `performances.program_status`, `program_source_url`, and `program_image_urls`
- Produces: `Performance.programStatus`, `programSourceUrl`, and `programImageUrls`

- [ ] **Step 1: Add a shared `ProgramPublicationStatus` type and optional source fields with seed-safe defaults.**

- [ ] **Step 2: Select and map the new Supabase columns and label NOL program rows as `NOL 원문`.**

- [ ] **Step 3: Render unlinked program rows as text and render a status-specific empty state instead of an empty list or `/works/` link.**

- [ ] **Step 4: Run `pnpm --filter @classic-hubble/shared test`, `pnpm --filter web test`, and `pnpm --filter web lint`; fix any regression.**

### Task 5: Live verification and operations documentation

**Files:**
- Modify: `workers/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: completed CLI and migrated database
- Produces: reproducible operator commands and verified live sample output

- [ ] **Step 1: Document NOL endpoint coverage, status semantics, request/retry behavior, and the `--enrich-nol` opt-in command.**

- [ ] **Step 2: Apply the new migration to the connected Classic Hubble Supabase project and verify schema advisors remain free of new security findings.**

- [ ] **Step 3: Run `nol-check` against one text-program product and one image-only product, then run a small `kopis-sync --enrich-nol --limit 5`.**

- [ ] **Step 4: Run the complete Python, TypeScript, lint, and production-build verification commands from the root README.**
