# Search-First UI Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, per the repository's main-thread-only instruction.

**Goal:** Replace the catalog dashboard with a minimal autocomplete-first concert search.

**Architecture:** Separate draft input/suggestions from committed query/results. A bounded, invoker-rights PostgreSQL RPC returns eight lightweight suggestions; existing search and work-detail readers remain authoritative after submission.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind 4, Supabase PostgreSQL, Vitest, Playwright.

## Global Constraints

- Approved spec: `docs/superpowers/specs/2026-11-02-search-first-ui-design.md`.
- No Redis, Elasticsearch, LLM call, catalog rewrite, or plan upgrade.
- Supabase project `klnfamtwxwrelrjeguqb` only. Preserve unrelated dirty files.
- Suggestions: maximum 8, 100ms debounce, IME-safe, 20-entry/60-second browser cache.
- Empty home does not load catalog rows or counts. Preserve original search rules.
- Stay on current dedicated branch; do not create another chat or worktree.

## U1: Bounded Suggestions and Exact Selection

Files: `apps/web/src/lib/work-suggestions.ts`, its test, `apps/web/src/app/api/catalog/suggest/route.ts`, its test, `apps/web/src/app/api/catalog/selected-work/route.ts`, its test, a CLI-created SQL migration.

```ts
type WorkSuggestion = { slug: string; title: string; composer: string };
getWorkSuggestions(query: string): Promise<WorkSuggestion[]>;
// GET /api/catalog/suggest?q=... => { suggestions: WorkSuggestion[] }
// GET /api/catalog/selected-work?work=slug&offset=0 => CatalogSearchResult
```

- [x] Add failing tests: empty input skips DB, one bounded RPC, RPC errors propagate, query length validation, exact slug selection and 24-row pagination.
- [x] Run focused Vitest files and verify new behavior is absent.
- [x] Add normalized prefix indexes and SQL using existing keys/aliases; apply only this additive migration. Return no programs/counts.
- [x] Implement cached service and validated endpoints. Selection calls `getCatalogWorkBySlug(slug)`, not free-text search. Use `/api/catalog/selected-work` to preserve the existing watchlist selection endpoint.
- [x] Verify SQL against known aliases, punctuation and limits. Security advisor check remains in final verification.

## U2: Search Interaction and Empty Home

Files: `SearchBox.tsx`, `SearchExperience.tsx`, `SearchResults.tsx`, their tests, `app/page.tsx` and its test.

```ts
type SearchState = { query: string; work: string; mode: "works" | "performances"; city: string };
// SearchBox owns draft text, focus, IME and suggestions.
// onSubmit(query) commits free-text; onSelect(suggestion) commits exact slug.
// SearchExperience owns URL state. SearchResults owns cached result pages.
```

- [x] Add failing tests for no initial DB reads, draft versus submit, selection, IME Enter, keyboard escape, stale responses and empty query reset.
- [x] Implement central empty search, compact submitted search, URL restoration and composer links.
- [x] Preserve mode, city, paging, retry and cached page deduplication.
- [x] Run focused and all web tests. Replace obsolete live-search expectations while retaining regression coverage.

## U3: Visual System and Detail Continuity

Files: `AppHeader.tsx`, `SiteFooter.tsx`, `WorkCard.tsx`, `PerformanceCard.tsx`, `app/layout.tsx`, `app/globals.css`, work/performance detail pages and tests.

- [x] Add failing header tests for hidden review links and accessible auxiliary navigation.
- [x] Apply white/neutral/green restrained styling, small wordmark, secondary menu and named icon controls.
- [x] Replace large result cards with compact rows and actual poster thumbnails. Remove detail framing while retaining evidence, dates, scope, relationships and booking links.
- [x] Retain license attribution in a compact footer.
- [x] Run header/detail/shared-card regressions and type/lint/build checks.

## U4: Browser Verification and Delivery

- [x] Inspect desktop and 390px/320px mobile screenshots: empty, suggestions, results, selected work, both details.
- [x] Exercise arrows/Enter/Escape, back navigation, clearing, login and pagination in-browser; cover IME and errors at component level.
- [x] Measure suggestion bytes and input-to-visible latency for cold/warm requests; avoid full catalog downloads.
- [x] Review diff, run full tests/build, preserve unrelated files, record evidence and provide local URL.
- [x] Confirm PR 111 status before integration; distinguish local/preview from production.

Verification: `docs/evaluation/search-first-ui-2026-11-02.md`. Preview: `http://localhost:3001`.
242 tests passed, 7 skipped; lint and production build passed. PR 111 remains open. UI integration/deployment is pending the user's next choice.
