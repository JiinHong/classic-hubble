# YouTube work search

## Operation

Open `/youtube` from the home search link. A supported YouTube video URL is
converted to a video ID, and the server retrieves title, description and channel
name through `videos.list`. Audio, captions, automatic chapters and YouTube's
music attribution cards are not retrieved. No YouTube account login is required.

`YOUTUBE_API_KEY` belongs in the web server environment only. Restrict it to
`youtube.googleapis.com` in the existing GCP project. Never use a `NEXT_PUBLIC_`
prefix. Configure Production and the intended Preview branch in Vercel, then
redeploy. A missing key produces a clear unavailable state rather than demo data.

## Candidate rules

- Only known YouTube hosts and a single valid video ID are accepted. User URLs
  are never fetched by the server; requests use the fixed official API endpoint.
- Composer, exact catalogue number, title and aliases identify candidates.
  Conflicting known composer, work number or key rejects a candidate.
- Explicit description lines and timestamped entries can produce several works.
  An ambiguous entry shows at most three candidates with its evidence text.
- Composer-only aliases do not identify a work. Numbered movement lines must
  belong to the uniquely identified parent work before being suggested.
- A component remains a distinct work. Concerts are not copied between a
  collection and its pieces. Results are suggestions, never verified audio facts.

## Boundaries and safeguards

Provider calls time out after 8 seconds. Client input is limited to 4096 bytes.
The process cache has at most 256 entries, valid for 60 seconds. Expired entries
are removed on the next request or process exit. No YouTube metadata is written
to the database. The UI links to YouTube, its terms and `/youtube/privacy`.

The per-process limit is 10 requests per minute per forwarded client IP, with a
bounded client map. It is not a distributed abuse or global quota guarantee.
Monitor Google API quota when traffic grows; do not treat this local limit as a
billing cap. Raw video URLs, provider responses and keys are not application logs.

Matching currently runs against the existing catalog snapshot in the browser,
consistent with the text-search surface. Large-catalog initial transfer and
slow-device latency remain scaling work. No accuracy percentage is claimed:
video descriptions can mention unrelated works, aliases can be incomplete, and
the canonical database does not include every composition or movement.

## Verification (2026-10-21)

- TDD: URL, matcher, endpoint and UI tests failed before implementation. Live
  metadata exposed composer-only alias and unrelated-movement regressions;
  dedicated failing tests preceded both fixes.
- A real browser exposed Next.js internal URL versus public Host mismatch.
  The regression test failed with 403 before the Host-based origin fix.
- 159 shared/web tests and 423 worker tests passed. ESLint and production build
  passed, including TypeScript checks.
- Live videos `vSYQMtiGry0` and `fuPrcnpIRx8` returned metadata and identified
  Beethoven Symphony No. 5 against the 12,435-work snapshot.
- Desktop and 390x844 mobile browser search showed the actual thumbnail and
  candidate. Mobile document width equaled viewport width (390px). The work
  detail link opened correctly and showed no confirmed upcoming performances.
- Sequential in-thread review covered URL/API trust boundaries, matching,
  errors, cache bounds, stale responses and UI navigation. This was not an
  independent multi-agent or cross-model review.

Rollback: revert the feature commit or promote the preceding Vercel deployment.
No schema migration or data rollback is required. Revoke the dedicated Google
key if the integration is removed permanently.
