# Image OCR operations

## Scope

The `ocr-worker` Cloud Run job reads all currently archived source hashes from the
private R2 bucket, without an item-count cap. It uses CPU PaddleOCR, not a vision
LLM or a paid OCR API. The catalog and source-archiver images remain separate.
An execution takes a snapshot: images archived afterwards are picked up on the
next execution. Completion of a snapshot does not establish full catalog coverage.

Pipeline: verified R2 bytes -> EXIF orientation and white alpha background ->
overlapping 1,600-pixel tiles -> PP-OCRv5 mobile detection and Korean recognition
-> original-image coordinates -> spatial duplicate removal -> private OCR JSON.
Identical text at different positions is retained. English text is recognized by
the Korean model, but accented Latin characters and decorative fonts need quality
evaluation. Tile borders can still split long lines; this is not a layout parser.

Results are evidence only. The worker does not update program_items, announce a
program change, send alerts, or establish whether a program has been published.
`no_text` means no text was recognized, not that the source contains no program.
Recognition scores are model scores, not calibrated correctness probabilities.

PDF processing is not implemented in this image worker yet. PDFs, animated images,
corrupt files and images above 40 million pixels receive an explicit
`needs_manual_handling` state. The per-file resource limit is not a catalog cap.
PDF text extraction/rendering remains part of delivery unit 2.

## Storage and retry

- Full output: `ocr/sha256/<prefix>/<sha256>` in `classic-hubble-sources`.
- Small completion record: private `provider_records`, provider `paddleocr`,
  entity type `ocr_result`, key `<pipeline_version>:<source_sha256>`.
- Metadata includes source/result keys and hashes, dimensions, line count,
  duration, processing time, status and `review_status=unverified`.
- Output JSON includes text, four-point polygons, bounding boxes and scores.
- Identical original bytes share one OCR result even across source URLs.
- Changed bytes or a new pipeline version require a new result; prior evidence
  is retained. Bump PIPELINE_VERSION when models, dependencies or preprocessing
  change. Official model archive SHA-256 values are fixed in bundle_ocr_models.py.
- The JSON must be durable before a completion record is published. If metadata
  writing fails, rerunning can safely reuse the immutable JSON object.
- `ocr_error` records contain exception class, not source text or raw responses.
  These files remain pending. Five consecutive inference failures stop a run;
  storage and database failures stop immediately. Inspect errors before retrying.

Successful text/no-text and manual-handling results are cached per pipeline.
Manual handling therefore needs a new pipeline version or an explicit reviewed
retry action after the input-handling capability changes. Do not blindly remove
completed records to force a rescan.

## Runtime and credentials

Project `classic-hubble-prod-20261021`, region `asia-northeast3`.
Job `ocr-worker`: 1 vCPU, 2 GiB, one task, parallelism one, no task retries,
1,800-second hard timeout and a 1,500-second soft deadline checked between files.
A single file may continue beyond the soft deadline. A hard kill may replay that
file on resume and can leave an ingestion run marked running.

The soft deadline records `partial` and the remaining count, then exits normally.
Only `remaining=0` establishes completion of that execution's source snapshot.
Run one execution at a time: task parallelism is not a cross-execution lock.
No OCR schedule or automatic retry chain is enabled. Add locking, cost monitoring
and failure reporting before routine scheduling.

Runtime account `ocr-worker@...` reads only version 1 of `supabase-secret-key`,
`r2-access-key-id` and `r2-secret-access-key`. It receives no KOPIS/LLM key.
The models are bundled into the container at build time with hash verification;
runtime model downloads are disabled by requiring local model directories.

The existing GCP budget is KRW 10,000/month; its alerts and Cloud Run spend cap
are not an exact hard limit. OCR runtime, builds, registry and secrets consume
that budget. R2 is billed separately. Measure the full corpus before setting a
daily cadence. No GPU or always-on endpoint is provisioned.

## Build and run

Build with `workers/cloudbuild-ocr.yaml`, using the existing worker-builder
service account and build-source bucket described in gcp-operations.md. Deploy
the resulting digest to ocr-worker, not the catalog jobs. Keep the verified digest
tagged `production-ocr-worker` to protect it from registry cleanup.

```sh
gcloud run jobs execute ocr-worker \
  --project=classic-hubble-prod-20261021 --region=asia-northeast3 \
  --account=pjh563319@gmail.com --wait
```

Before rerunning, check Cloud Run executions to ensure none is still active.
The bucket remains private. Read a result using R2Store.read(result_object_key)
on the server with its secret configuration; no public bucket URL is created.

## Verification

- Python suite: 199 passed. Web/shared: 75 passed; ESLint and Next.js build passed.
- Initial GCP smoke execution `ocr-worker-d6pps` processed five source images
  into 349 text lines with zero reported errors, then exited successfully with
  `status=partial`. Its 90-second soft deadline was checked between files, so
  the final 90-second image extended total processing to about 167 seconds.
  This is not a complete-corpus or average-cost measurement.
- Readback from private R2 verified the saved JSON hash, source identity,
  line count and four-point coordinates against its database completion record.
- TDD: missing image functions, result storage, batch resume and SIGTERM behavior
  were observed failing before implementation/fix.
- Tests cover tiling, coordinates, duplicate suppression, malformed images and
  engine output, private metadata pagination, hash identity, result persistence,
  resume, version changes, explicit unsupported media and deadlines.
- Local real-model checks used three archived KOPIS images, including a
  750 x 3,506 image processed as three tiles. These are integration checks, not
  a measured OCR accuracy benchmark or evidence of complete corpus processing.
- The image model reads biography and marketing text as well as program text.
  The following extraction stage must separate program entries from mentions
  of works in biographies; OCR alone must never publish those as performed works.

## References

- [PaddleOCR pipeline](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html)
- [PP-OCRv5 multilingual recognition](https://www.paddleocr.ai/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html)
