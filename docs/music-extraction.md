# Grounded Music Extraction

## Delivered boundary

`music_review` prepares a **text-only** request from an existing private OCR result
and validates/imports a separately supplied JSON response. It does not call an
LLM, use image input, create canonical works, publish a program, or send alerts.
The producer label is supplied by the operator; it is not proof of a model call.
No new public table, service endpoint, paid provider or scheduled job is enabled.

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
- All results, including unique matches, are `unverified` and `publishable=false`.
  Exact quotes do not establish semantic correctness, correct field association,
  or extraction completeness. `no_program_identified` is not evidence that the
  organizer has not published a program.

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
manual case), and **four canonical works**. This is partial OCR coverage, not a
completed backfill. A chosen text LLM/key, provider-specific schema adapter,
bounded batch inference and cost tracking, an evaluation set, catalogue expansion,
and an administrator review/publication interface remain to be implemented.
