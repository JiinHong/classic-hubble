# Original source storage

## Scope

`source-archiver` stores all introduction-image URLs attached to KOPIS performances
overlapping the catalog window. By default this is three calendar months before
through six months after the Korean collection date. Set both `COLLECTION_START`
and `COLLECTION_END` to use an explicit inclusive date range instead. An incomplete
or reversed range is rejected before any run or source writes. There is no
record-count cap. Poster-only URLs,
NOL pages and arbitrary third-party files are not part of this job.

Original bytes go to `classic-hubble-sources` in Cloudflare R2. The account-level
S3 endpoint is configured separately from the bucket, with region `auto`. URLs
from KOPIS are fetched on its HTTPS apex host; redirects and unrelated hosts are
rejected. Files are streamed with a 32 MiB per-file limit. Supported signatures
are JPEG, PNG, GIF, WebP and PDF; HTML error pages are not saved as images.

The worker performs no OCR or text-LLM requests. It does not update reviewed
programs, send notifications or prove a semantic program change. Those stages
can later read the preserved originals.

## Storage and metadata

- Object key: `originals/sha256/<first-two-hash-characters>/<sha256>`.
- Identical bytes reuse the same object, even when supplied by different URLs.
- A replaced image gets a new object; the previous bytes are not overwritten.
- Downloads through `R2Store.read` verify their SHA-256 before returning bytes.
- Private Supabase `provider_records` rows with provider `r2` store the latest
  `source_archive` pointer, `source_version` evidence and `source_error` records.
- Metadata includes source URL, performance IDs, object key, byte count, type,
  hash and check time. It contains no access keys.

The version row is written before the latest pointer advances. An interrupted
write can leave an unreferenced object, but retry reuses it rather than duplicating
the bytes. A successful same-date rerun skips saved sources. The next date fetches
them again to detect replacements at unchanged URLs. There is no automatic
retention/deletion policy yet; monitor storage growth before routine scheduling.

This deployment does not enable R2 public access or change CORS. Keep original
files private. A future review UI should receive short-lived access through an
authorized server route, not the storage credentials.

## GCP job

- Project: `classic-hubble-prod-20261021`; region: `asia-northeast3`.
- Runtime account: `source-archiver@classic-hubble-prod-20261021.iam.gserviceaccount.com`.
- One task, one vCPU, 512 MiB, 3,600-second timeout, zero automatic task retries.
- Secret Manager: `r2-access-key-id:1`, `r2-secret-access-key:1`,
  `supabase-secret-key:1`. Only the runtime needs access to these secret values.
- Non-secret environment: `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_REGION`,
  `SUPABASE_URL`; optional execution-only `COLLECTION_DATE`, `COLLECTION_START`
  and `COLLECTION_END`.
- Container command: `python -m classic_hubble_pipeline.source_archive`.

Build the shared worker container using `docs/gcp-operations.md`, then update only
this job with the successful build digest:

```sh
gcloud run jobs update source-archiver \
  --image=asia-northeast3-docker.pkg.dev/classic-hubble-prod-20261021/workers/collector@sha256:DIGEST \
  --region=asia-northeast3 --project=classic-hubble-prod-20261021
```

After verification, keep the digest tagged `production-source-archiver`. The
registry's `production` prefix retention rule preserves it independently of the
catalog job's `production` tag. Do not move the catalog tag for an archive-only
deployment.

## Run and recover

```sh
gcloud run jobs execute source-archiver \
  --region=asia-northeast3 --project=classic-hubble-prod-20261021 --wait
```

To finish a previous day's interrupted sweep, pass its original date:

```sh
gcloud run jobs execute source-archiver \
  --update-env-vars=COLLECTION_DATE=2026-10-21 \
  --region=asia-northeast3 --project=classic-hubble-prod-20261021 --wait
```

Run only one source-archiver execution at a time. Per-execution task limits are
not a distributed lock. A source HTTP 401, 403 or 429 stops the sweep; five
consecutive download failures also stop it. Other individual source failures
are recorded while remaining sources continue. Any source error makes the final
run status failed so missing files do not silently pass. Storage or database
errors stop the run without advancing the failed source's pointer.

For a historical backfill, first finish catalog collection and compare its official
ID list with the database. Archival only sees performances already in the database;
successful archival alone does not establish complete catalog coverage. Then run:

```sh
gcloud run jobs execute source-archiver \
  --update-env-vars=COLLECTION_START=2024-01-01,COLLECTION_END=2026-10-22,COLLECTION_DATE=2026-10-22 \
  --region=asia-northeast3 --project=classic-hubble-prod-20261021 --wait
```

Resume an interrupted historical sweep using the same three settings, including
the original `COLLECTION_DATE` even when resuming on another day. This skips durable
source pointers already checked for that sweep; changing the date deliberately
refreshes the files. `checked_at` still records the actual wall-clock check time.
Keep these settings execution-only so routine runs retain their rolling window.

Inspect both Cloud Run execution status and private `ingestion_runs` rows with
provider `r2`; a hard kill may leave the latter running. Successful source pointers
remain resumable. Counters report discovered URLs, archived/reused/changed/skipped
sources, errors and newly uploaded bytes. The URL count can exceed the object
count because identical bytes are shared.

No Cloud Scheduler or GitHub schedule invokes this job yet. Add locking and
failure reporting before switching the existing daily workflow to GCP. Avoid
running the old and new collection schedules concurrently.

## Costs and verification

R2 usage is billed separately from the GCP project budget. GCP processing and
outbound transfers, Secret Manager, builds and registry storage still need
monitoring; content deduplication does not eliminate daily source downloads.

The initial live test uploaded a 228,953-byte KOPIS JPEG, downloaded byte-identical
content, and reused the object on a repeated archive call. This is a storage
connectivity check, not proof that the full source catalog has been archived.

Cloud Run execution `source-archiver-zpzjk` started on 2026-10-21 from digest
`sha256:eba672fa10e89a7ab475ee10583e98a5b52d4cb90398a499d7de60bc29cbaa12`.
It discovered 4,774 unique source URLs. A readback of a 439,188-byte object saved
by that execution matched its stored hash and metadata. The first database
verification found 172 saved source pointers; the full sweep was still running.
Use execution status and run counters for its terminal result, not this snapshot.

References: [Cloudflare boto3 configuration](https://developers.cloudflare.com/r2/examples/aws/boto3/)
and [Cloud Run job secrets](https://docs.cloud.google.com/run/docs/configuring/jobs/secrets).
