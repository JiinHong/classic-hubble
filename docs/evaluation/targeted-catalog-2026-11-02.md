# Performance Search and YouTube Candidate Retrieval

## Scope

Performance search and YouTube identification no longer call `getCatalogSnapshot`.
The existing TypeScript search and identification rules remain authoritative.
SQL retrieves a superset of candidates, with no arbitrary top-N cutoff.
Component families are expanded before matching. YouTube upcoming links are
loaded only for final selected works, preserving chronological order.
Performance search reads lightweight matching metadata, then full details for
the displayed page only. Candidate-query failures return 503, not a full scan
or a false empty result.

Migration `20261102015203_targeted_performance_youtube_candidates.sql` was applied
to Classic Hubble (`klnfamtwxwrelrjeguqb`). Functions use invoker rights and an
empty search path. The security advisor returned no warnings before and after.
The migration adds derived search keys and an upcoming-date index; source work,
composer, performance, and program values are unchanged.

## Measurement

Measured on the user's Mac against the same Supabase database on 2026-11-02.
The baseline contains 12,733 works and 24,106 non-demo performances. It is saved
locally and reused for comparison, not downloaded for every input.

Cold baseline preparation: 3,889.89 ms, 38 DB HTTP responses, 21,869,508 decoded
response-body bytes (works 5,786,040; performances 16,083,468).
The old-time column below adds this single measured preparation time to each
input's measured old matching time. These are not independent repeated cold
requests. The new-time column measures each targeted lookup plus matching.

| Input | Old preparation + matching | New lookup + matching | Old DB bytes | New DB bytes | Reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Performance: Beethoven (Korean) | 4,227.06 ms | 260.78 ms | 21,869,508 | 209,444 | 99.04% |
| Performance: Fate nickname (Korean) | 3,994.91 ms | 707.20 ms | 21,869,508 | 5,976 | 99.97% |
| Performance: empty browse | 3,893.00 ms | 218.35 ms | 21,869,508 | 344,774 | 98.42% |
| YouTube: Beethoven Symphony No. 5 Op. 67 | 4,026.37 ms | 165.23 ms | 21,869,508 | 201,847 | 99.08% |
| YouTube: Frederic Chopin Nocturne Op. 9 No. 2 | 3,892.34 ms | 178.00 ms | 21,869,508 | 247,243 | 98.87% |

Across 9 performance inputs and 14 YouTube metadata fixtures, complete results
matched, including totals, order, aliases, component relations, ambiguity,
reasons, timestamps, and upcoming performance IDs. The broad Bach-conflict
fixture returned more candidates (944,901 bytes), still 95.68% below baseline.

Important limitations:
- Byte counts are decoded DB HTTP response bodies, not compressed wire bytes,
  client response sizes, or Supabase billable egress measurements.
- YouTube timings exclude the external video metadata API. Fixtures avoid
  repeated video API calls; no new OCR or paid extraction was used.
- A warm old catalog can require zero DB bytes and faster matching for a new
  query. These cold-path results do not imply every warm request is faster.
  Repeated identical new requests retain the existing 60-second caching.
- Database buffers were not flushed; timings are observations, not latency SLAs.
- Date-sensitive comparisons require a baseline from the same Seoul day.
- Unsupported scripts and punctuation intentionally over-select candidates;
  SQL's lossy key never determines a public match.

An initial test disabled all Next caches, incorrectly counting the old
compressed-group fallback's page reads twice (37,952,976 bytes). That run is
superseded, preserved for audit, and is not used for the reduction figures.
The corrected harness preserves within-run page reuse.

The original production HTTP probe separately measured 14.143 s total, including
11.830 s catalog preparation and 1.187 s search. It is not directly comparable
to local test timing. Its 15,543 bytes were API-to-browser bytes, not DB bytes.

## Verification

- Shared tests: 27 passed; web tests: 226 passed, opt-in live tests skipped in default CI.
- Live old/new comparison: 23 inputs passed.
- Lint, TypeScript, and production build passed.
- Browser: desktop 1440x1000 and mobile 390x844, Beethoven performance search and
  pagination returned 200, no page errors or horizontal overflow.
- Manual diff review covered candidate recall, ambiguity preservation, parent
  expansion, pagination beyond 1,000 rows, link ordering, error propagation,
  grants, and derived-column impact. No unresolved blocker was found. No
  independent reviewer or external review model was used.

Local evidence directory:
`/Users/parkjinhong/Documents/Codex/2026-07-08/new-chat/artifacts/targeted-performance-youtube-20261102/`

Authoritative measurements:
`baseline-cache-aware.json` and
`baseline-cache-aware.json.comparison-1793584738734.json`.

Re-run from `apps/web` with a new local snapshot path for a new Seoul date:

```sh
TARGETED_CATALOG_COMPARE=1 TARGETED_CATALOG_SNAPSHOT=/absolute/private/snapshot.json \
  node --env-file=.env.local node_modules/vitest/vitest.mjs run \
  src/lib/targeted-catalog.integration.test.ts
```
