# NOL Deterministic Adapter Design

## Goal

Enrich KOPIS classical-performance records with information that NOL exposes as deterministic HTML or JSON, without OCR or LLM interpretation. The first production path follows booking links already supplied by KOPIS, extracts the Interpark/NOL goods code, and reads NOL's ticket-front JSON endpoints.

## Scope

The adapter supports official Interpark/NOL ticket URLs containing an eight-digit goods code, including legacy `GoodsInfo.asp?GoodsCode=...` URLs and current `/goods/...` URLs. It reads:

- `/v1/goods/{goodsCode}/summary` for title, venue, ticket metadata, detail HTML, and detail images.
- `/v1/goods/play-db?goodsCode={goodsCode}` for a dedicated `programInfo` field when NOL has created a Play DB record.

Curated NOL editorial routes that do not expose a goods code, venue-specific collectors, OCR, work canonicalization, and automated browser scraping are outside this increment.

## Deterministic Classification

The adapter assigns one program publication status:

- `confirmed`: a dedicated program text produced one or more deterministic program blocks.
- `selected_on_day`: the source explicitly says the program will be selected or disclosed at the performance.
- `announced_later`: the source explicitly says the program will be announced later.
- `image_only`: no machine-readable program text exists, but the NOL detail consists of one or more images that may contain it.
- `not_published`: neither program text nor detail images are available.
- `unknown`: no NOL enrichment has completed yet.

`programInfo` takes precedence over the general detail HTML. If it is empty, the parser looks for an exact `PROGRAM`, `PROGRAMME`, `프로그램`, or `공연 프로그램` heading in the detail HTML and parses only the following section. It never treats biographies or general descriptions as a program.

Program text is split only at explicit blank separators. A leading composer is separated only when it includes a lifespan marker such as `(1756-1791)`; otherwise the whole block remains the display title. Movements stay attached to their parent work. This favors faithful source storage over speculative structure.

## Safety And Reliability

- User-supplied and KOPIS-supplied URLs are accepted only for known official Interpark/NOL hosts.
- All data requests go to the fixed HTTPS API host `api-ticketfront.interpark.com`; source URLs cannot redirect the worker to another host.
- HTTP 429 and temporary 5xx failures use bounded exponential retry.
- Raw NOL responses are stored in `provider_records` before normalized fields are updated.
- A NOL failure increments `nol_errors` but does not discard the successful KOPIS record.
- Re-running a sync replaces only NOL-owned program rows, leaving rows from other providers untouched.

## Storage Contract

`performances` gains `program_status`, `program_source_url`, `program_image_urls`, and `program_source_updated_at`. `program_items` gains `source_provider` and `source_url`, plus a unique key on `(performance_id, source_provider, position)`.

NOL text rows use `source_provider = 'nol'`, `source_type = 'verified'`, and `confidence = 0.98`. They intentionally keep `work_id = null` until the existing alias normalizer can resolve a canonical work. Raw responses use `provider = 'nol'`, `entity_type = 'performance_detail'`, and the goods code as `provider_id`.

## User Experience

Confirmed text appears as normal program entries even when no canonical work is linked yet. An unlinked entry is plain text rather than a broken work-page link. Empty programs display the precise publication status, including the important distinction between image-only information and information that has not been published.

## Operations

`nol-check --url ...` provides a read-only diagnostic snapshot. `kopis-sync --enrich-nol` enables NOL enrichment during the existing KOPIS sync. The opt-in flag keeps the baseline KOPIS job independent from NOL availability and makes the additional external request volume explicit.
