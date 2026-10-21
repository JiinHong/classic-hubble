# Grounded Music Extraction

## Delivered boundary

`music_review` prepares a **text-only** request from an existing private OCR result
and validates/imports a separately supplied JSON response. It does not call an
LLM, use image input, create canonical works, publish a program, or send alerts.
The producer label is supplied by the operator; it is not proof of a model call.
No new public table, service endpoint, paid provider or scheduled job is enabled.

An opt-in `openai_music` adapter and offline evaluation path are now available.
The adapter sends text to GPT-6 Luna, records billed input/cache/output usage,
retains usage on invalid responses, and never retries automatically. It does not
by itself run a worker or publish to the website. The 53-document pilot was a
separate, explicitly authorized API run; the replay below makes no API calls.

The request contains the schema, extraction instructions, OCR document hash and
stable line IDs with zero-based page indices. It contains no credentials, source
URLs, original images, DB IDs or object-storage keys. OCR text itself can contain
personal information from a poster: review provider terms before sending it.
Source text is untrusted data, not model instructions.

## Validation and matching

- Composer, title, catalogue number, key and movements reference exact OCR quotes.
  Multiline fields use ordered quote lists; spelling corrections are not invented.
  Quote boundaries prevent matching `Op. 18` inside `Op. 180`.
- Strict types, required fields, forbidden extras, duplicate JSON keys, unknown
  line IDs, mismatched document hashes and invented quotes fail closed. Limits:
  1 MiB response, 200,000 OCR characters, 10,000 lines and 200 references. Exceeding
  a limit fails explicitly, without truncating a document. Chunking is not built.
- Actual programs, biography references and unknown context remain distinct.
  Full works, movements, excerpts, arrangements and unknown scope remain distinct.
- Reuse composer/catalogue/alias matching. Non-program references cannot produce
  a performance suggestion. Partial/uncertain scope and unsupported key notation
  require review. The current matcher does not support every catalogue or language.
- In the legacy private import workflow, all results, including unique matches,
  are `unverified` and `publishable=false`.
  Exact quotes do not establish semantic correctness, correct field association,
  or extraction completeness. `no_program_identified` is not evidence that the
  organizer has not published a program.

## Automatic evaluation policy (v2)

`validate_response(..., automatic=True)` preserves valid items independently.
The document envelope/hash remains strict. Invalid item schemas or source quotes
are returned in `rejected_items` with an original index, reason and failed field.
`validation_status` is complete, partial or failed; it is not an accuracy score.
An inconsistent document status prevents publication even if quotes are valid.
The original model response and evidence remain unchanged in the evaluation set.

- Korean particles and joined Korean text are allowed in exact quotes. ASCII
  numeric boundaries still reject `Op. 18` quoted from `Op. 180`. A joined `in`
  prefix is supported specifically for key evidence.
- Structured matching supports bilingual names, lifespans, initials, Korean
  spacing/number styles, quoted nicknames, bilingual keys, catalogue members in
  aliases, and multiple catalogue systems recorded for the same work.
- Composer ambiguity, conflicting numbers/keys, multiple matches and generic or
  composer-only titles do not auto-link. One-character OCR composer typos produce
  candidates only. Imported canonical IDs can link without human approval when
  the identity evidence is unique; no new work IDs are invented.
- `suggested_work_id` is reserved for full-work suggestions. `scoped_work_id`
  retains an identified work with its movement/excerpt/arrangement/unknown scope;
  it is not necessarily a parent work and is not a full-work publication.
- A movement list cannot establish completeness. Non-first listed movements
  override a model's full-work label; other movement lists remain scope-unknown.
- Multiple explicit month/day performance dates in one source prevent automatic
  assignment of all listed works to a single concert. This is a guard, not a full
  date parser; performance-specific date binding remains to be implemented.
- `publishable` describes eligible full-work suggestions only. `complete` is a
  separate flag and cannot be true with invalid/unresolved program items.

No public DB writes, automatic retries, paid scheduling or notifications are
enabled by this policy. Human approval is not the planned production gate;
grounding, uniqueness, scope and source freshness are.

## Offline replay

Use a private directory containing `catalogue.json` and one directory per OCR
hash with `ocr.json` and `extraction.json`. Replay has no network/provider writes,
requires a new output directory, and creates mode-0600 reports/CSV files.

```sh
.venv/bin/python -m classic_hubble_pipeline.music_replay \
  --input /private/path/to/evaluation \
  --output /private/path/to/new-replay
```

This reuses paid responses; changing the extraction prompt requires a separate
new model run. The revised prompt has unit tests but has not yet been re-evaluated
with live inference. Never describe cached-response replay as a prompt benchmark.

## Private prepare/import workflow

Run from the repository root with its ignored `.env`. `OCR_SHA` is the
`result_sha256` of a current private `provider_records` OCR result, **not** the
original image hash. Use a private directory outside Git for requests/responses.

```sh
.venv/bin/python -m classic_hubble_pipeline.music_review prepare \
  --ocr-sha "$OCR_SHA" --output /tmp/classic-hubble-request.json

.venv/bin/python -m classic_hubble_pipeline.music_review import \
  --ocr-sha "$OCR_SHA" --response /tmp/classic-hubble-response.json \
  --producer manual-annotation

# Explicitly save private review candidates, not public concert programs:
.venv/bin/python -m classic_hubble_pipeline.music_review import \
  --ocr-sha "$OCR_SHA" --response /tmp/classic-hubble-response.json \
  --producer manual-annotation --apply
```

Prepare creates a new mode-0600 file and refuses to overwrite it. Import defaults
to a read-only count report. It verifies stored OCR bytes and metadata, checks
that the original still belongs to the current archive, and rejects superseded
OCR results. The source is rechecked before storage. A subsequent administrator
approval must recheck source/OCR/catalogue freshness again; no atomic publication
or approval workflow is implemented here.

Apply stores immutable JSON at private R2
`extractions/sha256/<prefix>/<sha256>` **before** upserting small private metadata
with provider `music_extraction`, entity `extraction_candidate`. A failed R2/DB
write marks the run failed and can be retried. Identical inputs produce identical
candidate IDs; response, contract, producer, source or catalogue changes produce
new IDs. Coordinates remain in the original OCR evidence, linked by its hash.
Candidate records never update `program_items` or notification tables.

## Verification and remaining work

The tests cover text-only requests, fabricated evidence/IDs, numeric truncation,
biography/partial works, conflicting keys, unknown works, stale/corrupt sources,
storage/DB failures, idempotent retry, dry-run behavior and private CLI files.
They use annotated fixtures, not model responses and not an accuracy benchmark.

A live read-only check on 2026-10-21 prepared 224 OCR lines without calling an LLM.
At that check there were 55 OCR records (53 text results, one empty result, one
manual case). The later evaluation snapshot contains 12,435 canonical works.
This is partial OCR coverage, not a completed backfill.

The 2026-10-21 replay of 53 saved responses retained 232 of 241 references:
48 documents fully validated, 3 partially validated and 2 with no valid items.
There were 18 full-work suggestions and 15 separately scoped identifications
across 14 documents. These are references, not 33 unique works or a measured
accuracy. The original 6 full-work suggestions included one partial-work error.
The replay corrected that overstatement and made zero additional paid calls.

Remaining: semantic/coverage evaluation on held-out annotated posters; source
date binding; catalogue/alias data quality; selective re-extraction of malformed
items; scoped-work UI/DB publication; and a resumable, budgeted worker plus an
atomic source-freshness-checked publication transaction. No new production job
is deployed by this change. Existing NOL/manual program entries must be preserved.
