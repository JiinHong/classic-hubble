# Full Service Delivery

## Approved Scope

The user's 2026-10-21 diagrams define the complete product, not a sample-only
collector. Preserve Vercel and Supabase. Use GCP for collection and processing,
Cloudflare R2 for source files, PaddleOCR for images, and a text-only LLM for
structured music information. Match extracted works against a canonical database.
Include Resend email alerts, YouTube metadata search, and Amplitude analytics.
Community channels collect feedback; they are not automatic integrations unless
separately requested.

## Constraints

- Initial GCP budget: KRW 10,000/month on the existing billing account.
- No vision LLM, no GPU or always-on server by default.
- No arbitrary performance-count limit for production collection.
- Initial catalog window follows the prior plan: past 3 months, next 6 months.
  This is all returned classical records in that window, not every historical
  concert or guaranteed coverage of every venue.
- Respect provider access restrictions. NOL HTTP 403 is unresolved; changing
  hosting does not establish permission or guarantee successful access.
- Secrets stay outside source and container images. Missing credentials do not
  justify fake success or silently selecting a paid provider.
- TDD for behavior changes. Execute and review sequentially in this thread.

## Delivery Units

1. GCP foundation and complete KOPIS collection: dedicated project, project-only
   budget, bounded Cloud Run runtime, container packaging, checkpoint/resume,
   and an actual full-range run. Existing GitHub collection remains until the
   replacement is verified; avoid two active schedules after cutover.
2. Source processing: R2 source objects with content hashes, same-URL replacement
   detection, PDF text extraction or rendering, PaddleOCR text and coordinates,
   retryable processing states. Preserve original evidence and program changes.
3. Music information and matching: schema-constrained text LLM output with source
   spans; expand canonical composers, works and aliases; evaluate precision and
   abstain on ambiguity. Administrator review must precede uncertain publication.
4. Search: work and composer filters, performance detail and external booking
   links; YouTube Data API title/description parsing, multiple-work selection and
   explicit invalid/private/insufficient-metadata states. No audio recognition claim.
5. Alerts: authenticated watchlists, consent, deduplicated notification outbox,
   Resend delivery with unsubscribe and provider-event handling. Domain and sender
   verification are prerequisites for real mail to users.
6. Analytics and release: Amplitude event definitions for acquisition, search,
   watchlist, notification, return visit and booking clicks; privacy controls,
   mobile end-to-end tests, operational dashboards and source attribution.

## Current Implementation Unit

Files: workers/src/classic_hubble_pipeline/{kopis,kopis_sync,supabase,cloud_run}.py;
workers/tests/{test_kopis,test_kopis_sync,test_supabase,test_cloud_run}.py; workers/Dockerfile;
workers/{requirements-cloud.txt,.dockerignore,.gcloudignore,cloudbuild.yaml};
docs/gcp-operations.md.

Verification: first prove missing resume behavior with failing tests, then verify
that checkpoints include only fully persisted performances, failed runs preserve
progress, a completed run exits without repeating writes, and a fresh run date
refreshes all records. Run the full Python suite and build the container. Verify
GCP IAM, budget scope, secret references, image digest and actual job results.
No schema change is needed: private provider_records can store checkpoints and
isolated source request failures. Access/rate limits and repeated failures must
stop collection rather than silently hammering a provider.

## External Prerequisites

Local configuration currently contains working KOPIS and Classic Hubble Supabase
credentials. R2 is configured and source archival is running. A chosen text LLM,
Resend verified sender, YouTube API key and
Amplitude project key are not configured. These are recorded prerequisites, not
completed features. Additional paid service usage requires a cost decision.

## Source Processing Progress

R2 archival is shipped. Image OCR is implemented in a separate CPU Cloud Run job;
see `docs/ocr-operations.md` for its storage, retry and deployment contract.
PDF text extraction/rendering is now implemented in the same private processing
job. Native text is preserved; scanned and mixed pages go through PaddleOCR.
Unit 2 is still partial: broader PDF link discovery, semantic program-change
comparison and recurring orchestration remain. OCR evidence is not automatically
published as a program. Units 3-6 are not completed by image recognition.

## Music Processing Progress

Unit 3 now has a provider-independent grounded extraction contract, exact OCR
evidence validation, canonical review suggestions and a private prepare/import
CLI. See `docs/music-extraction.md`. No model is connected or called yet, and no
OCR-derived result is published. The catalogue still contains four works.
Canonical expansion, model evaluation and actual batch inference remain pending.
