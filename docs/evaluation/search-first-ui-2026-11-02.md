# Search-First UI Verification

Date: 2026-11-02
Branch: `design/search-first-ui`
Base: `92f2792` (`perf/targeted-performance-youtube`, PR 111)
Preview: `http://localhost:3001` (local production build)

## Scope

- The empty home now contains a wordmark and search field, without catalog counts, default results, nearby concerts or review navigation.
- Typing requests at most eight work suggestions. Submission keeps the existing search rules. Selecting a suggestion sends its exact work slug.
- Search results and work/performance details use compact, unframed layouts. Actual posters, program evidence, scope, upcoming/past concerts, login, watchlist and attribution remain available.
- No OCR processing, catalog content edits, external search service, paid model call or plan change was made.

## Automated Checks

- `pnpm --filter web test`: 43 files passed, 2 skipped; 242 tests passed, 7 skipped.
- `pnpm --filter web lint`: passed.
- `pnpm --filter web build`: passed, including TypeScript checking.
- `git diff --check`: passed.
- Empty-home component tests verify no overview/work search call. Browser capture records no initial `/api/catalog/` request.
- New coverage includes bounded suggestions, exact selection, error states, IME composition, keyboard controls, stale responses, cache expiry, pagination, URL restoration and whitespace clearing.
- Review found and fixed two interaction regressions with failing tests first: clearing a submitted query replaced the focused input; returning from a detail page reused stale initial props from Next.js's cached home. The URL is now the live search-state source, including when the component remounts.
- Keyboard selection scrolls the active suggestion into view. Main-thread review was performed; this was not an independent-agent review.

## Browser Checks

Playwright with local Chrome tested 1440x1000, 390x844 and 320x844, each in a fresh page at a fixed viewport.

- Empty home, suggestions, exact-work results, work details, performance results and performance details passed overflow/header checks.
- Visible poster images loaded successfully with nonzero pixel dimensions.
- Arrow/Enter selection, Escape, detail-page back navigation, clearing with focus retained, menu navigation and login dialog passed.
- Pagination appended 24 results to 28 without replacement.
- No JavaScript page errors were observed.
- IME behavior and failure/retry paths were tested at component level; a real operating-system Korean keyboard and authenticated alert enrollment were not exercised.

Earlier resize-in-place screenshots contained stale composited content and one route capture preceded completed navigation. They are not final evidence. The final run waits for the destination heading and paint, and uses separate fixed-size pages.

Local evidence directory: `/Users/parkjinhong/Documents/Codex/2026-07-08/new-chat/artifacts/search-first-ui/final/`.
The report is `browser-report.json`; screenshots are named by viewport width and state.
The reproducible script is the sibling `final-browser.cjs`.

## Measured Suggestions

Single-run observations on the Mac against the real database, not a latency SLA or production-host measurement:

| State | Query | Input to visible | Browser requests |
| --- | --- | ---: | ---: |
| First desktop request | 라흐 피협 2번 | 1292.4 ms | 1 |
| First desktop request | 운명 | 1800.6 ms | 1 |
| Same-page browser cache | 라흐 피협 2번 | 11.6 ms | 0 |
| New mobile page, warm server | 라흐 피협 2번 | 185.2 / 185.6 ms | 1 each |

| API query | HTTP time | JSON body bytes | Suggestions |
| --- | ---: | ---: | ---: |
| 라흐 피협 2번 | 12.8 ms | 138 | 1 |
| 운명 | 1.9 ms | 215 | 2 |
| 베토벤 | 177.6 ms | 853 | 8 |

API samples were taken after the interaction run, so some were server-cache hits. Bytes are response-body bytes, not billed Supabase egress or total network traffic. First-use suggestions are still slower than an instant local response; additional cold-query optimization remains possible. Navigating away destroys the component-local result cache, so returning to the selected work requests that targeted result again. The selected-work reader also retains the existing detail reader's past-performance fetch, although this endpoint returns only upcoming performances.

## Database and Release State

- Applied only `20261102023740_search_first_work_suggestions.sql` to `klnfamtwxwrelrjeguqb`.
- Adds three prefix indexes and the bounded `suggest_works(text)` invoker-rights function, with an empty search path and explicit role grants. No catalog rows or public work links were changed.
- Anonymous-role checks confirmed the expected first result for `라흐 피협 2번`, `라흐피협2번`, `브바협`, `운명`, and `베토벤 교향곡 5번`; all returned no more than eight suggestions. Short-prefix and empty/punctuation/no-match cases were also checked.
- The Supabase security advisor returned no lints during this implementation.
- PR 111 was still OPEN with no merge timestamp at final verification. This UI work is separate and has not been pushed, merged or deployed to the production website.
- Existing OCR-related dirty files and the unrelated incomplete migration were left untouched.
