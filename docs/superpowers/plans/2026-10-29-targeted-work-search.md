# Targeted Work Search Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans, sequentially in this chat as requested.

**Goal:** Stop loading the complete work/performance catalog for work searches and the homepage, without changing matching rules.

**Architecture:** Indexed SQL retrieves a conservative candidate superset. The existing shared matcher retains ranking, aliases, shorthand, numeric boundaries and component validation. Only displayed works receive upcoming-performance IDs; the homepage receives aggregate counts and four concerts.

**Tech Stack:** Next.js, TypeScript, Vitest, Supabase/PostgreSQL pg_trgm.

## Global Constraints

- Preserve unrelated dirty files and existing original catalog records.
- No arbitrary candidate cap or silent partial results on database errors.
- Public read functions use security invoker and existing RLS.
- Existing performance-tab search remains unchanged in this scoped change.
- Deploy database additions before the application; compare the same queries with the immutable 2026-10-29 baseline.

## Task 1: Targeted Search (In Progress)

Files: shared search anchor helper/tests; `apps/web/src/lib/work-search.ts` and tests; small exports from `catalog.ts`; `20261029081505_targeted_work_search.sql` (CLI-created file aligned to the version returned by the applied migration).

Interfaces: `getWorkSearchAnchor(query): string`; `getWorkSearchPage(query = "", offset = 0): Promise<CatalogSearchResult>`; `getHomeOverview()` returns work/upcoming/confirmed counts and up to four performances.

- [x] Add failing tests for 24-row browse, candidate pagination, component expansion, unchanged shorthand matching, page-only performance lookup, and error propagation.
- [x] Run `pnpm --filter web test src/lib/work-search.test.ts`; confirmed missing-module failure before implementation.
- [x] Implement indexed normalization/candidate RPC, minimal upcoming links and homepage aggregates. Reuse existing `mapWorks`, `mapPerformances`, `attachWorkComponents`, and shared matching.
- [x] Run focused tests and verify SQL normalization against shared normalization on explicit cases. Example contract: `getWorkSearchAnchor("라흐 피협 2번") === "피아노"`. Six opt-in anonymous integration tests passed.

## Task 2: Switch Callers

Files: search route/tests and homepage/tests.

- [x] Add regression assertions that work mode and home never call `getCatalogSnapshot`; retain performance mode and unavailable responses.
- [x] Replace work-mode route and home reads; retain CDN headers and expose targeted-load timing.
- [x] Run `pnpm test`, `pnpm lint`, `pnpm build`; review numeric, alias, parent-context, errors and public-data boundaries. 27 shared and 219 web tests passed; six network tests are opt-in and passed separately.

## Task 3: Release and Measure

- [x] Apply reviewed additive migration to project `klnfamtwxwrelrjeguqb`; verify anonymous RPCs, indexes, and unchanged source records. Source fingerprints matched before/after for all 12,657 works, 40,683 aliases and 302 composers. Security advisors returned no findings.
- [ ] Commit only task files, open/attach PR, check CI, integrate through existing release procedure.
- [ ] Confirm Vercel production READY; run the same browser/curl timing protocol into a new artifact directory.
- [ ] Report actual cold/cache behavior, result parity, transferred candidate sizes, and limitations. Do not describe cached timing headers as fresh database execution.

## Operational Notes

- Generated search keys are updated automatically by PostgreSQL when source fields change. If shared normalization changes, update the SQL normalizer and regenerate stored keys in a migration; run the opt-in normalization contract checks.
- Short queries can require broad candidate reads. Results are never capped before ranking. The performance tab, admin review and YouTube catalog routes retain their existing loaders.
- Roll back the application deployment first if needed. The additive database columns/functions may remain; dropping them is not required to restore the previous app.
- Review: the dedicated multi-agent CE review could not run under this task's main-thread-only instruction. Manual scoped review covered SQL/RLS/input escaping, data preservation, numeric and component recall, pagination, unavailable responses, and cache separation; no blocking findings remained. No independent peer review is claimed.
