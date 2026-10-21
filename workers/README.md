# Classic Hubble Workers

Python workers cover the ingestion path that should stay outside the Next.js request cycle.

## Jobs

- `kopis.py`: validates query windows, paginates KOPIS v5.0 performance and facility XML responses, retries temporary failures, and keeps raw provider payloads.
- `nol.py`: validates official NOL/Interpark goods URLs and deterministically extracts program text or publication state from NOL ticket-front JSON.
- `kopis_sync.py`: maps KOPIS records and optionally enriches NOL-linked performances before writing normalized program rows.
- `supabase.py`: writes worker data through the Supabase Data API with a server-only secret key.
- `cli.py`: exposes key-safe KOPIS/NOL diagnostics and synchronization commands.
- `work_matching.py`: conservatively matches explicit program text against the canonical works and aliases stored in Supabase.
- `program_matching.py`: previews or applies matches for existing unlinked NOL program rows.
- `ocr.py`: placeholder only. The planned image reader is OCR, not a vision LLM; image recognition is not operational yet.
- `normalizer.py`: legacy prototype with a small hardcoded catalogue; it is not used by the ingestion matcher.
- `notifications.py`: prototype matching helpers; production email and web-push delivery are not implemented here.

## Local Commands

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e 'workers[dev]'
.venv/bin/python -m pytest workers/tests
```

## KOPIS Connectivity Check

Create a root `.env` from `.env.example` and set `KOPIS_API_KEY` when the key is available. The key is read only by the Python worker and must never use a `NEXT_PUBLIC_` variable.

```bash
.venv/bin/classic-hubble-pipeline kopis-check \
  --start 2026-07-01 \
  --end 2026-07-31 \
  --rows 10
```

The command fetches one page of classical performances and prints only IDs and display fields as JSON. It never prints the API key. KOPIS limits performance-list windows to 31 calendar days and pages to 100 rows; the client validates both limits before a request.

## NOL Deterministic Check

NOL enrichment does not require an API key. The adapter accepts only official Interpark/NOL goods URLs and sends all data requests to the fixed `https://api-ticketfront.interpark.com` host.

```bash
.venv/bin/classic-hubble-pipeline nol-check \
  --url https://tickets.interpark.com/goods/26007299
```

The output includes the goods code, title, venue, publication state, image URLs, and parsed program blocks. It intentionally omits the large raw HTML/JSON payload. `programInfo` text is split only at explicit blank separators; a composer is separated from the work only when the source includes a lifespan. No OCR or LLM interpretation is used.

Publication states are:

- `confirmed`: one or more machine-readable program blocks were extracted.
- `image_only`: NOL provides detail images but no machine-readable program text.
- `not_published`: neither program text nor detail images are available.
- `selected_on_day`: the source says the program will be disclosed at the performance.
- `announced_later`: the source says the program will be published later.
- `unknown`: NOL enrichment has not completed.

## KOPIS to Supabase Sync

Set `SUPABASE_URL` and a server-only `SUPABASE_SECRET_KEY` in the root `.env`. A legacy `SUPABASE_SERVICE_ROLE_KEY` remains supported as a fallback. Never put either server key in a `NEXT_PUBLIC_` variable.

Start with a small live batch:

```bash
.venv/bin/classic-hubble-pipeline kopis-sync \
  --start 2026-07-01 \
  --end 2026-07-31 \
  --limit 5 \
  --enrich-nol
```

`--enrich-nol` is opt-in so the baseline KOPIS job remains independent from NOL availability and the extra request volume is explicit. The sync follows the first valid NOL goods link supplied by KOPIS, stores the raw NOL response first, and then replaces only NOL-owned program rows. A temporary NOL failure increments `nol_errors` without discarding the successful KOPIS performance. Any NOL error marks the overall run failed and exits the command with status 1; the first error is included in the stored run summary. Re-running the same range updates by provider natural keys and does not duplicate NOL program rows or review images.

## Canonical Work Matching

New NOL rows are linked only when the composer and an explicit catalogue number or exact title/alias identify one database work. Conflicting work numbers/keys, ambiguous composers, excerpts, and mixed program blocks remain unlinked. A source-derived match is labelled `official`, not human-`verified`. These rules are intentionally conservative and are not an accuracy guarantee.

Preview existing unlinked NOL rows without modifying production data:

```bash
.venv/bin/classic-hubble-pipeline program-match
```

The JSON report includes candidates and reasons. After reviewing that report and the canonical catalogue, explicitly apply accepted deterministic matches:

```bash
.venv/bin/classic-hubble-pipeline program-match --apply
```

The command reads all candidate rows before writing and updates only rows that are still unlinked, still NOL-owned, and whose source title/composer have not changed. `matched` counts proposed matches; `updated` can be smaller if a concurrent edit made a row ineligible. No canonical works are invented or automatically inserted. See `docs/evaluation/README.md` for the real-source evaluation backlog.

The NOL ticket-front endpoints are used by NOL's public web client but are not a versioned public Open API. Their response shape can change. Keep the live `nol-check` command in deployment smoke tests and treat sustained parser errors as an adapter update signal, not as permission to guess missing data.

The sync accepts longer ranges and splits them into KOPIS-compliant 31-day windows. Every run is recorded in `ingestion_runs` with counters and a terminal status.

The full collector can use `KopisClient.iter_performances()` to traverse every performance page and `get_performance_detail()` to collect cast, schedule text, introduction images, and booking links. `iter_facilities()` and `get_facility_detail()` cover facility and hall records, including seat counts, coordinates, accessibility, parking, and stage metadata. HTTP 429 and temporary 5xx responses are retried with exponential backoff. `KOPIS_MAX_RETRIES=3` means one initial request plus up to three retries. A repeated full page fails loudly instead of silently hiding incomplete pagination. Requests are restricted to the official KOPIS HTTPS host and do not follow redirects to another destination. KOPIS result codes such as an invalid key are raised separately from network failures.

The July 2026 KOPIS v5.0 guide contains a facility-detail overview typo that names the `pblprfr` path. Its request example and the facility-list API use `prfplc`, which is the path implemented here. The common-code guide confirms `CCCA` as `서양음악(클래식)`.

The live KOPIS API item page documents response codes `00` through `06`. List parsers treat `04` (`NODATA ERROR`) as an empty page so pagination can stop normally. Codes `01`, `02`, `03`, `05`, and `06` remain explicit `KopisApiError` failures; in particular, `05` identifies a query window over 31 days and `06` identifies a page size over 100 rows.

Real jobs should write raw provider responses first, then normalized records. Low-confidence OCR results should enter `poster_review_items` instead of being published directly.

Any public screen backed by KOPIS must display the required attribution: `출처: (재)예술경영지원센터 공연예술통합전산망(www.kopis.or.kr)`.
