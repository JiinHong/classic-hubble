# GCP collection operations

## Scope and deployment

The production collector has no performance-count cap. It enumerates all KOPIS
classical records returned for the three calendar months before and six calendar
months after the Korean collection date. On 2026-10-21 the inclusive range is
2026-07-21 through 2027-04-21. This is not a claim of all historical concerts or
complete coverage of every venue. Missing programs remain missing, not inferred.

- Project: `classic-hubble-prod-20261021` (`925874878641`).
- Region: `asia-northeast3` (Seoul).
- Cloud Run job: `catalog-collector`.
- Runtime: Python 3.11, 1 vCPU, 512 MiB, one task, parallelism one.
- Each execution stops after 3,600 seconds; automatic task retries are disabled.
- Registry: `asia-northeast3-docker.pkg.dev/classic-hubble-prod-20261021/workers/collector`.
- Database: the existing Classic Hubble Supabase project, `klnfamtwxwrelrjeguqb`.

The catalog worker collects KOPIS API data and registers image URLs. A separate
`source-archiver` job now downloads these originals to R2; see
[R2 operations](r2-operations.md). Neither job runs OCR, calls a text LLM, or
sends email. NOL enrichment is not enabled in these jobs; the previously observed
HTTP 403 remains unresolved. Remaining product work is tracked in
`superpowers/plans/2026-10-21-full-service-delivery.md`.

## Budget boundaries

The existing billing account is linked to this dedicated project. Other projects
and the user's default gcloud configuration were not changed.

- Project-wide monthly budget: KRW 10,000, alerts at 50%, 80%, and 100%.
- Cloud Run service spend cap: KRW 7,000/month, state `CONFIGURED`.
- Both track spend excluding credits, scoped only to this project's charges.
- The Cloud Run cap blocks new billable service usage after enforcement, but
  reporting and enforcement lag can allow overage. Running work and other
  services are not an exact KRW 10,000 project-wide hard limit.
- Build, registry, secrets and storage consume the remaining allowance. Free
  allowances may be shared with other projects on the same billing account.
- R2, LLM, Resend and any paid Supabase/Vercel/Amplitude usage are outside this
  GCP budget. Do not activate paid tiers without a separate cost decision.

No VM, GPU, always-on HTTP server, load balancer or VPC connector was provisioned.
This configuration is a starting envelope, not evidence that full OCR and LLM
processing will fit the monthly budget. Measure documents, pages and token usage
before choosing a processing frequency or paid model.

## Credentials and IAM

`collection-worker@...` is the runtime service account. It has Secret Accessor
only on the two secrets `kopis-api-key` and `supabase-secret-key`. The job pins
secret version 1, so rotation requires deploying the replacement version reference.
The Supabase server secret is privileged: never expose it to the web client.

`source-archiver@...` is a separate runtime account with Secret Accessor only on
`r2-access-key-id`, `r2-secret-access-key` and `supabase-secret-key`. These references
also pin version 1. The catalog collector does not receive R2 credentials.

`worker-builder@...` has Artifact Registry Writer on the workers repository,
Storage Object Viewer on the build-source bucket and Logs Writer on this project.
The automatically created Compute Engine account's broad Editor grant was removed.
No service-account key file was created. Local deployment uses the signed-in user.

`workers/.gcloudignore` and `.dockerignore` allow only worker sources and build
inputs. Production environment files, tests and capstone documents are excluded.
The container runs as UID/GID 10001. Keep secret values out of commands and logs.

## Build and deploy

Run from the repository root. Always specify the project rather than changing the
global default. Set a unique image tag and use the successful build's digest for
deployment, not a mutable tag.

```sh
gcloud builds submit workers --config=workers/cloudbuild.yaml \
  --substitutions=_IMAGE=asia-northeast3-docker.pkg.dev/classic-hubble-prod-20261021/workers/collector:UNIQUE_TAG \
  --service-account=projects/classic-hubble-prod-20261021/serviceAccounts/worker-builder@classic-hubble-prod-20261021.iam.gserviceaccount.com \
  --gcs-source-staging-dir=gs://classic-hubble-prod-20261021-build-source/source \
  --region=asia-northeast3 --project=classic-hubble-prod-20261021

gcloud run jobs update catalog-collector \
  --image=asia-northeast3-docker.pkg.dev/classic-hubble-prod-20261021/workers/collector@sha256:DIGEST \
  --region=asia-northeast3 --project=classic-hubble-prod-20261021
```

After verification, move the `production` image tag to the deployed digest. The
registry cleanup policy preserves that tag and the three newest images, and
removes other builds older than seven days. Its background cleanup is not instant.
The dedicated build-source bucket deletes staging objects after one day, with
soft delete disabled. Git remains the source of truth, not those temporary copies.
Policies are versioned under `infra/gcp/` and apply only to these new resources.

## Execution, recovery and scheduling

```sh
gcloud run jobs execute catalog-collector \
  --region=asia-northeast3 --project=classic-hubble-prod-20261021 --wait
```

With no override, the job uses today's Asia/Seoul date. To resume an interrupted
sweep on a later day, pass its original date as an execution-only override:

```sh
gcloud run jobs execute catalog-collector \
  --update-env-vars=COLLECTION_DATE=2026-10-21 \
  --region=asia-northeast3 --project=classic-hubble-prod-20261021 --wait
```

Private `provider_records` rows keyed by `catalog-v1:YYYY-MM-DD` track fully saved
performance IDs. Progress is flushed every 25 performances and on handled exit.
Only successful writes, including any requested NOL enrichment, can advance a
record. Failed source detail requests are recorded in private `collection_error`
rows, excluded from the checkpoint, and retried on the next execution. Successful
records can continue to be collected while an individual source request fails.
A hard kill can replay the unflushed tail; existing natural-key upserts
avoid duplicate concert records. A failed checkpoint write can require more replay.
A completed sweep is a no-op on same-date rerun; the next date refreshes the range.
This is daily snapshot behavior, not real-time detection or an hourly refresh.

Run only one collector execution at a time. Cloud Run parallelism limits tasks
inside an execution, not the number of separate executions. Checkpoints are not a
distributed lease. HTTP 401, 403 and 429 stop collection instead of continuing
through the catalog. Five consecutive source transport failures also stop the
sweep; there is no unbounded retry loop. Malformed XML, API-level errors and DB
write failures still stop the sweep and need investigation. A hard kill can leave the old
ingestion-run row marked running, so inspect Cloud Run status as well as the DB.

No Cloud Scheduler schedule has been activated. The existing GitHub daily workflow
remains unchanged until a verified cutover; it does not invoke this GCP job yet.
Before cutover, add execution locking, replace the old KOPIS schedule rather than
duplicating it, and include failure reporting. Checkpoints are retained for recovery;
a retention policy will be needed after routine scheduling begins.

## Verification

- Python worker suite: 172 tests passed, including catalog resume, source errors,
  access/rate-limit stops, R2 integrity, source revisions and recovery after a
  metadata write failure.
- Web/shared tests: 75 passed; ESLint and production Next.js build passed.
- Initial container built successfully in Cloud Build and was deployed by digest.
- Initial full-range execution `catalog-collector-m8fct` saved 528 performances
  before a KOPIS HTTP 400. Execution `catalog-collector-grtbq` resumed and saved
  another 20 before a different request returned HTTP 400. Both records were
  subsequently available from the official API. This exposed the need for
  per-record error isolation, which was added with regression tests.
- Independent list enumeration on 2026-10-21 found 3,205 unique performances in
  the selected range. Execution `catalog-collector-h7jzd` succeeded at
  2026-10-21T02:43:51Z; its checkpoint contains all 3,205 completed IDs and
  `complete=true`. This verifies the selected KOPIS range, not all historical
  concerts or every venue.

## References

- [Cloud Run task timeout](https://docs.cloud.google.com/run/docs/configuring/task-timeout)
- [Budget spend caps and their limitations](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps)
- [Artifact cleanup policies](https://docs.cloud.google.com/artifact-registry/docs/repositories/cleanup-policy)
- [Cloud Run pricing](https://cloud.google.com/run/pricing)
