# YouTube work search

Implements delivery unit 4 of the approved full-service plan. The user selected
YouTube search ahead of review/publication. Existing OCR and ingestion stay unchanged.

## Contract

- `/youtube`, linked from the existing search surface, accepts a video URL.
- Parse only known YouTube hosts and watch/shorts/live/embed/short-link paths.
  Extract a single 11-character video ID; never fetch a user-supplied URL.
- A server-only `YOUTUBE_API_KEY` calls `videos.list(part=snippet,id=...)`.
  No account access, audio download, scraping, captions or automatic-chapter claim.
- Match title and explicit description lines/timestamps against existing work
  names, aliases, composer identity and catalogue numbers. Metadata is evidence
  for suggestions, not verified audio contents. Do not call a paid LLM.
- Several explicit entries produce a selectable list. Each ambiguous entry has
  at most three candidates, with its original text and matching reason visible.
  Unknown entries stay unknown. Never inherit concerts from parent/child works.
- Work links use existing detail/booking flow. Distinguish no identified work,
  no confirmed upcoming performance, unavailable video, invalid URL, quota,
  timeout, configuration error and upstream failure.
- No DB writes or persisted YouTube metadata. A bounded process cache lasts
  60 seconds; per-process throttling is best-effort, provider quota is the final
  aggregate limit. Secrets and raw submitted URLs are never logged.
- Show YouTube source links and data-use/terms/privacy notices. No fake results.

## Implementation and verification

1. Test URL parsing and metadata candidate matching before implementing pure
   helpers. Include catalogue-prefix collisions, composer conflicts, component
   identity, ambiguous candidates, multi-piece descriptions and unhelpful tags.
2. Test fixed-endpoint API access, upstream errors, missing keys, body/origin
   checks, bounded cache and request throttling before implementing the route.
3. Test loading/error/empty/multiple-candidate rendering and stale-response
   cancellation before implementing the page. Reuse existing WorkCard and detail
   links; preserve current text search behavior.
4. Enable the API and create a YouTube-only server key in the existing GCP
   project. Configure Vercel secrets without printing key values. No paid upgrade.
5. Run all web/shared tests, Python regression tests, lint and build. Review the
   scoped diff sequentially, verify desktop/mobile UI and real API cases, then
   ship via GitHub CI and confirm the production deployment and source SHA.

## Boundaries

This is metadata-driven candidate retrieval, not measured music-recognition
accuracy. A video may mention works that are not played. New composer spelling
variants and weak metadata can remain unmatched. Corpus-wide OCR, administrator
publication, alerts and changes to canonical DB relationships are out of scope.

## Official references

- https://developers.google.com/youtube/v3/docs/videos/list
- https://developers.google.com/youtube/v3/docs/videos
- https://developers.google.com/youtube/terms/developer-policies
