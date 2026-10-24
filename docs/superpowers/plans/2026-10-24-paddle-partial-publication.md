# Paddle Partial Publication Implementation Plan

> **For agentic workers:** Execute inline using executing-plans. No subagents or new chats.

**Goal:** Process the existing 999-image OCR backlog through grounded matching and publish only verified individual works, stopping at 30% remaining account allowance.

**Architecture:** Keep PaddleOCR observations immutable. Store separate text-reviewed selections with exact source quotes. Recompute conservative matches and date binding against current evidence, then submit eligible full works to an atomic service-only RPC. Always label this path partially_confirmed; do not assert complete OCR coverage.

**Tech Stack:** Existing Python workers, private R2/provider_records, PostgreSQL RPC, shared TypeScript status and existing Next.js presentation.

## Global Constraints
- No new OCR, GCP jobs, paid model calls, schedules or chats.
- Protect manual, NOL and direct-vision programme rows; preserve previous evidence and publication history.
- Single current image and single performance date, matching the OCR date, remain required for this version.
- Only explicit composer plus catalogue/alias full-work matches may publish; excerpts, arrangements, conflicting dates, ambiguous identities and low-confidence cited OCR lines remain private.
- An OCR engine score is not an accuracy estimate. Missing scores fail the publication check.
- Batch completion means a saved matching/publication outcome or a specific unresolved reason, not OCR completion.

## Tasks
- [x] Add failing Python tests for partial eligibility, immutable provenance, scores, stale evidence and date/scope rejection; add failing web status test.
- [x] Implement `paddle_publication.save_review` and `publish`, reusing `_current_ocr`, `validate_response` and `_date_matches`; add repository methods.
- [x] Add separate enum and guarded RPC migrations; test inside rollback transactions including other-provider preservation, idempotence, malformed and stale payloads.
- [ ] Add the partially_confirmed UI message; run worker/web suites and build, review named changes, ship through GitHub/Vercel and verify production.
- [ ] Reconstruct the exact 999-image cohort, preserve a fresh private baseline and process bounded reviewed-text batches. Verify writes and report image/performance/item counts separately.
- [ ] Group unresolved cases, repair only evidence-backed failures with regression tests, and stop at the allowance boundary with an immutable handoff.

## Verification Commands
` .venv/bin/python -m pytest workers/tests/test_paddle_publication.py ` must fail before implementation, then pass with the full worker suite.
` pnpm --filter web test src/lib/format.test.ts ` must fail for the new status before implementation, then pass with web/shared suites.
SQL tests run with `BEGIN; ... ROLLBACK;` against klnfamtwxwrelrjeguqb only. New enum value is committed separately before testing the RPC. No public writes before deployment and successful verification.

## Approved Design
The user approved option 1: independently verified works may be published even when other works remain unresolved, with a visible partial-programme label. No further changes to identity or scope requirements are authorized by this approval.
