# Grounded Music Extraction

## Direct image reading for the initial historical backfill

The user's 2026-10-22 direction overrides the OCR runtime for the initial
2024-01-01 through 2026-10-22 backfill: use the local Mac, archive originals in
private R2, then show actual image pixels to the model in this conversation.
Do not install/run PaddleOCR or substitute new OpenAI API image/text calls for
this work. Conversation usage still consumes Codex allowance. Historical OCR
and the 53 Luna responses retain their original provenance.

`direct_vision.prepare(repository, store, source_sha, output_directory)` exports
a hash-verified R2 original and `reading-request.json` into a new private
directory (0700, files 0600). It never calls a model. An operator/agent must
actually view the original using the image viewer, or render and inspect PDF
pages, before writing the response. A file export or a hash is not evidence that
the pixels were read. Long images require readable region views; incomplete
viewing is `coverage=partial`, not a claim to have read the entire source.

The response schema retains the original source hash, timezone-aware observation
time, coverage, visible text lines with zero-based page indices, and music fields
quoted from those lines (`L000000`, `L000001`, ...). It rejects extra confidence,
coordinate and model-ID fields rather than fabricating them. `no_text`,
`unreadable`, and text with `no_program_identified` are separate outcomes; none
proves that the organizer has not published a program.

`direct_vision.import_reading(..., raw_bytes, apply=False)` validates the response
and runs the existing conservative matcher. `apply=True` stores immutable private
R2 evidence and an insert-only `provider_records` row under `codex_vision` /
`direct_reading`. Identity includes the source hash, bucket, method and pipeline
version. Repeated identical imports reuse the first observation; another reading
cannot silently replace it. Corrupt caches fail instead of triggering new reads.
Storage completes before the DB completion record; a lost DB acknowledgement can
be reconciled by reading that record. No historical OCR row is renamed or edited.

The saved envelope includes transcription, source URL/association snapshot,
grounding evidence, work candidates and match reasons. It is limited to 1 MiB so
it can be read back through the same bounded JSON parser. The schema and exact
quote checks do not establish visual transcription accuracy. Public performance
associations must be checked against current data separately.

Biography-only and series-poster observations with no work items do not load the
work catalogue. They retain text/no-program evidence and cannot become confirmed
programs simply because their ingestion completed.

**Current boundary:** this adapter only persists private observations and match
reports. `published_items` is always zero. It does not add works, replace NOL or
manual data, send alerts, or create a human approval queue. A source-current
atomic publication transaction and bounded batch orchestration remain to be
implemented. Cached matching reflects the catalogue at import time, not future
catalogue changes. `eligible_for_publication` only describes full-work candidate
eligibility with complete image coverage, not permission to skip publication's
source, scope, performance-date and ownership checks.

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

## Durable paid-response cache

`music_cache.MusicResponseCache` persists exact request identities in private
`provider_records` (`openai` / `music_request`). The cache key is a digest of the
complete wire body, including the OCR hash, text, instructions, schema and model.
Original extracted JSON, request body, response ID and usage are kept in private
R2; small DB metadata records cost estimates and the content-addressed pointer.

A unique insert claims the request before inference. Duplicate or concurrent
requests cannot replace that claim. Completed results are read back with hash,
bucket, request and document identity checks. Claimed, failed, corrupt or missing
results never silently fall back to another paid call. A crash or an uncertain
network outcome requires reconciliation; claims do not expire automatically.
Known billed tokens survive API/storage failures when available. Unknown charges
retain the conservative request estimate, not zero. A lost DB acknowledgement
can leave a claim even if R2 succeeded; do not delete it to force a paid retry.

`import_result` accepts an operator-verified historical `InferenceResult` with
usage and its original request bundle. Before importing saved evaluations, compare
the saved wire body with `OpenAIMusicClient.body(bundle)` and parse the saved API
response through the existing adapter with an offline transport. Importing is
idempotent and never invokes the model. Historical costs are marked separately
from live attempts so importing does not count as new spending.

This is response storage, **not source freshness validation or publication**.
The caller must select current OCR before inference and revalidate freshness in
the eventual publication transaction. Cached JSON must still pass grounding and
current-catalogue matching. A scheduled `music_worker` and atomic public-program
writer remain separate work; this cache does not create either or send alerts.

For the finite 2024-01-01 through 2026-10-22 backfill the user approved proceeding
without a cumulative OpenAI spending cap. Keep bounded document/time batches,
record known and unknown charges, and do not retry uncertain paid attempts. The
separate GCP KRW 10,000 / Cloud Run KRW 7,000 limits remain in effect. Reported
token-based costs are estimates, not invoices, and exclude tax/FX/infrastructure.

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
- In composer fields only, a Korean compound surname such as
  `림스키-코르사코프` is compared as `림스키코르사코프`. The joined name must
  match an existing composer identity; fragments and conflicting names are not
  inferred. Raw quotes, title parsing, legacy matching and publication guards
  are unchanged.
- Explicit two-letter dotted abbreviations such as `Ch. Gounod` may match the
  given-name prefix and exact surname of an existing two-word Latin name.
  Undotted fragments, surname edits and omitted middle personal names are not
  inferred. Multiple composer identities and bilingual conflicts remain guarded;
  recognizing a composer does not establish a missing work or full-work scope.
- Composer ambiguity, conflicting numbers/keys, multiple matches and generic or
  composer-only titles do not auto-link. One-character OCR composer typos produce
  candidates only. Imported canonical IDs can link without human approval when
  the identity evidence is unique; no new work IDs are invented.
- Explicit full names `Johann Strauss II`, `Johann Strauss Jr` and `Johann Strauss
  Junior` identify the same composer. Full-name generation markers I and III stay
  distinct; I is not expanded as an initial of II. This is not a general rule
  equating every composer's Junior suffix with II, or resolving a bare Strauss.
  The [Vienna Institute for Strauss Research biography](https://www.johann-strauss.at/en/forschung/biografien/jss/)
  distinguishes Johann Strauss II from his father. Work, scope and date guards
  still apply after name recognition.
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
new model run. Never describe cached-response replay as a prompt benchmark.

The matching layer normalizes the OCR catalogue prefix `0p` to `Op` only for
search. It does not repair digits, discard conflicting catalogues, or change
the original fields/evidence. Scoped titles can remove presentation markers
such as `from` or a Korean closing quote followed by `중`, and use a delimited
parent title. Genre, number, catalogue and key constraints still come from the
**entire** title, including the suffix; a conflicting suffix cannot be hidden.

For separately extracted numbered ballades, composer-scoped title comparison
accepts `Ballades No. 1` as `Ballade No. 1`. The original plural evidence stays
unchanged. This does not fold a multi-number list/range into one work, remove
number/key/catalogue conflicts, resolve duplicate candidates, or expand the
composerless title index. The actual source must first establish each separate
number; the matcher does not invent a split from a collection title.

When the model puts separately numbered works in `movements`, an explicit work
genre and catalogue can recover individual identities. Each derived item has
the original `source_index`, a `derived_from` movement index and exact source
quotes. It has `scope=unknown`, `suggested_work_id=null` and a `scoped_work_id`;
identifying a listed work does not prove a full performance or a catalogue
parent-child relationship. Biography, status and multi-date gates still apply.

Replay counts `validated_items` as original model references and reports
`derived_items` and `evaluated_items` separately. `unique_document_work_pairs`
deduplicates repeated mentions of the same work in a document. Neither a link
count nor schema-validation success is an accuracy metric.

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

On 2026-10-22 a live v2 run produced 201 valid references across the same 53
documents, but only 28 distinct document/work links. Replaying those exact v2
responses after matcher fixes recovered all seven lost v1 links, with no v2 link
losses: 35 distinct document/work pairs across 15 documents. There are 14
full-work suggestions and 22 scoped references (one repeated mention), including
four derived constituent-work identities. All 201 original references remain
valid and unchanged; four derived references are reported separately. This
replay disabled network access, preserved the 12,435-work catalogue snapshot and
all saved inputs, made zero API calls and changed no public data. The remaining
140 unlinked program references are not all missed works: they include missing
composer information, non-work text, ambiguity and catalogue gaps. These 53
development documents are not a held-out accuracy benchmark.

Remaining: semantic/coverage evaluation on held-out annotated posters; source
date binding; catalogue/alias data quality; selective re-extraction of malformed
items; scoped-work UI/DB publication; and a resumable, budgeted worker plus an
atomic source-freshness-checked publication transaction. No new production job
is deployed by this change. Existing NOL/manual program entries must be preserved.

## Direct image observations and incremental publication (2026-10-22)

The historical backfill now uses images actually viewed in the chat model, not
an OCR engine or a separate model API. `direct_vision.prepare` exports verified
R2 bytes and a strict observation schema. `import_reading` stores immutable,
private evidence under the `codex_vision/direct_reading` provider record. It
does not itself publish. Cached observations are re-matched against the current
catalogue/rules; their original matching snapshot is not overwritten.

`vision_publication.publish` has a deliberately narrow initial publication
boundary: one current introduction image, one performance date, complete image
coverage and all program works matched with full-work scope. Multi-date or
multi-image sources, partial observations, excerpts and unresolved works stay
private until performance-specific binding and scoped publication are supported.
Korean/full-year date headings and ampersand-separated dates now trigger the
multi-date guard. This is still not a general date parser.
Publication also requires a transcribed date heading matching the performance
date. Missing or conflicting dates remain private, even when the works match.
An explicit full-year date on its own line may use the immediately following
weekday-only or weekday-and-clock line. Blank/intervening text, yearless wrapped
dates and weekday contradictions remain unresolved. Source lines are not joined
or rewritten in the saved observation; the normalized date still has to match
the SQL-locked performance date.

For a single-recital poster ending in the four-column Kumho annual series
calendar, `publish(..., series_calendar=True)` is an explicit alternative to
rejecting every date in the footer. It requires the full original observation,
including all four columns. The printed date and weekday, performer in the
headline and programme, and composer must agree with the target calendar cell.
Every public title, composer and catalogue number must be quoted within the
sole Program section, one complete work per line before Artist. A footer,
biography or another recital cannot supply a missing reference. Preview and the
locked transaction use the same digest-bound SQL proof. The stored observation
is unchanged. Other layouts still use the existing rules; see
`supabase/tests/direct_vision_series_calendar.sql`.

Before apply, the publisher verifies archived bytes and immutable reading hashes,
re-runs matching, and downloads the original URL to compare the live hash. One
service-role-only RPC locks the performance and source records, compares expected
snapshots and validates the submitted items against matching evidence. It writes
programs, confirmation state and a private before/after audit in one transaction.
NOL/manual/other provider items are preserved; such performances are skipped.
Repeating the same publication preserves row IDs and creates no duplicate items.
The external website can change after the final check; periodic recollection is
still needed. SQL regression checks are in `supabase/tests/direct_vision_publication.sql`
and roll back every synthetic fixture. No migration enables a paid worker/job.

Direct-reading program rows retain source provider `codex_vision`. The existing
required numeric confidence column uses its zero sentinel, not a measured
confidence; the web mapper exposes `null` and shows only the image-reading label.
The private audit retains the exact observation, hash references and matching
evaluation. Never describe this processing coverage as measured accuracy.

Replaying the 53 saved v2 results after the stricter date guard retains 14 full
work suggestions, while scoped references decrease from 27 to 22 (40 to 36
distinct document/work pairs; 17 to 15 documents with a suggestion). These are
withheld suggestions from ambiguous multi-date sources, not deleted public
links. Candidates remain available for performance-specific date binding. This
replay makes no additional model API calls and is not an accuracy benchmark.

## Private Reading Corrections

`vision_revision.promote_correction(repository, store, proposal_id, apply=False)`
previews a persisted `direct_reading_correction_proposal`. It verifies the private
R2 proposal, original bytes, old observation and corrected grounded reading.
`apply=True` saves a new immutable evidence object and invokes
`revise_private_direct_reading` to compare the expected old pointer, proposal and
current source associations in one transaction. A private `direct_reading_revision`
receipt retains both pointers. The original object and original observation are
never overwritten, and the normal importer still rejects conflicting readings.

This operation corrects private evidence only. It never publishes programme rows
or changes matching/date/scope rules. Any source with a prior publication audit
is refused with `published_source_requires_reconciliation`, even if its public
rows were later removed. Reading-row locks serialize revision with publication;
the publisher rejects a stale observation. Repeated promotion returns `unchanged`
without another upload; competing proposals return `stale` rather than overwrite
one another. Keep proposals immutable and use the revision receipt to determine
which correction became active, not the proposal's original pending status.

Run `workers/tests/test_vision_revision.py` and the rollback-only
`supabase/tests/direct_vision_revision.sql` when changing this contract. Apply the
revision migration before using the helper. Both RPCs remain service-role-only;
there is no new scheduled worker, separate OCR engine or model API call.

## Incremental matching batches (2026-10-22)

Matching improvements are regression-tested rules, not model training. For a
missing composer, only an exact distinctive title/alias that uniquely identifies
a catalogue entry is eligible. Explicit unknown/conflicting composers are not
ignored. A shared surname can be resolved by an exact distinctive title, never
by a catalogue number alone. Catalogue, key, genre and number conflicts still
block a link. Uniqueness within this database is not proof of global uniqueness.

Stored NOL text and new NOL ingestion now share `match_program_text`. It handles
explicit composer-only lines, delimited composer prefixes, conventional movement
labels and two bilingual headings that independently identify the same work.
Composer initials such as `L.` and `C.` are not treated as movements. Multiple
works, unknown extra lines and explicit excerpt/arrangement text remain unlinked.
Raw titles and composer fields are retained; only the canonical identity is linked.
This is not a verification of the performance's instrumentation or completeness.

The stored-program command defaults to a read-only batch of 50 (maximum 200):

```sh
.venv/bin/classic-hubble-pipeline program-match --batch-size 50
.venv/bin/classic-hubble-pipeline program-match --batch-size 50 --apply
.venv/bin/classic-hubble-pipeline program-match --batch-size 50 --after-id LAST_SCANNED_ID
```

Continue with the returned `next_after_id` while `has_more` is true. Applying a
batch removes matched rows from the unlinked set; an ID cursor avoids offset
skips. Start without a cursor after changing rules to reconsider old failures.
Apply checks that the row is still NOL, still unlinked, and its original title and
composer have not changed. It does not overwrite existing links, create works,
rewrite OCR/LLM evidence or send email. Keep each report in private storage for
comparison and recovery. A conflict between preview and apply requires a new
preview; the command's `updated` count can be lower than `matched`.

Five batches (50/50/50/50/24) evaluated all 224 then-unlinked NOL entries against
the same 12,435-work catalogue. The previous matcher linked none; the final rules
linked 33 entries across 22 performances. All 33 writes were read back and their
raw text was unchanged. The remaining 191 consist of 135 complex text blocks,
37 unconfirmed composers, 10 non-program labels/notices and 9 without a candidate.
`no_candidate` is a research queue, not proof that the work is absent: catalogue
metadata, aliases or matching rules may still be responsible. Never create a
new canonical work solely because the current matcher found no candidate.
`title_number_conflict` specifically means a recognized composer's catalogue
identity exists but a printed work number contradicts its canonical titles.
The source stays unlinked; the diagnostic does not repair numbering conventions
or discard a conflicting bilingual number. A valid supported candidate still
takes precedence, and missing catalogue identities remain `no_candidate`.

Two observed composer name forms have explicit primary-source support:
`드보르작` / `안토닌 드보르작` for Antonin Dvorak ([Daejeon venue programme](https://daejeon.go.kr/okr2019/pblcFcltView.do?menuSeq=8900&pageIndex=1&pblprfrInfoId=2078))
and `Mikhail Glinka` for the canonical Mikhail Ivanovich Glinka
([Edition Silvertrust](https://www.editionsilvertrust.com/glinka-sextet.htm)).
Grounded matching accepts these names and their existing initial conventions
only for those exact canonical identities. It does not infer arbitrary omitted
middle names, repair `Dvork`, or override conflicting bilingual composers.
Printed evidence remains unchanged; normal work-number, key and scope checks apply.

Full-work sonata matching also checks explicitly named instruments against primary
canonical titles. Muczynski's flute Sonata Op.14 must not satisfy an alto-saxophone
sonata merely because the supplied opus agrees. Piano accompaniment is optional
in instrument labels, but a piano sonata is not a flute or violin sonata. Missing
canonical instrumentation is not invented. Scoped parent candidates remain private
and retain their arrangement/movement evidence; this guard does not publish them.

The same 53 saved v2 OCR/LLM results increased from 35 to 40 distinct document/work
pairs across 17 documents (previously 15). All previous pairs were retained.
There are 14 full-work suggestions and 27 scoped references; these OCR results
were **not** published. This iteration made zero additional LLM calls. It did
not measure held-out accuracy or validate the remaining unprocessed images.

At this audit the public database contained 5,608 performances; the earliest
non-null start date was 2024-11-09. A complete 2023-to-present backfill has not been
verified and must not be described as already collected. Next iterations should
separate complex blocks into source-grounded individual works, research missing
catalogue entries/aliases, and expand OCR coverage before claiming full coverage.

### Typed KOPIS recital programmes

A cover with no programme is not negative evidence about the official KOPIS
detail. For a single-date Schubert song recital, a complete saved cover can
corroborate the concert's identity, composer, venue, date and clock. The song
list comes from the separately fetched, byte-checked `sty` field. It is never
added to the image reading. The literal title and complete Deutsch number must
identify the same live work in an independently archived authority. Ambiguous
settings and cycle members without an individually established identity stay
unlinked, without renumbering adjacent songs.

The service-only `publish_kopis_typed_recital` checks the locked performance,
official detail, original cover, reading and catalogue again before writing.
It records original source lines, a before/after history and both independent
source hashes. Existing programmes are preserved. Public items cite KOPIS as
official text, with no OCR accuracy or inferred performed edition.

A separate service-only path, `publish_kopis_text_program`, handles verified
KOPIS text blocks on dated orchestra and Salon de Musique recital covers.
Never infer titles from the cover or a performer's name. The worker checks the
original image, the existing cover observation, the native `[PROGRAM]` text,
and the archived publisher or rights-holder evidence separately. The database
independently checks each printed position, composer, canonical work, catalogue
number, date and room when it locks the current event. Unsupported rows retain
their original positions; an uncertain arrangement or edition is not published.
Named numbers from a parent work are excerpts, not performances of the entire
parent. Already published programmes are not replaced. Preview, write and
idempotent readback use the same evidence.

A numbered song can be linked to the individual song (not its cycle) when
the archived work catalogue agrees on the title, collection and number.
The live song must carry that member number in its Deutsch or documented
opus numbering; an alias on a parent is insufficient. An unchanged
previously published programme from these same sources may gain missing
rows. This never replaces, renumbers, or deletes an existing row, and
requires a matching prior publication audit.

### Gala programmes inside festival brochures

For a named single-composer gala, a separate event calendar can corroborate
the programme even when the surrounding festival spans several days. Both
the calendar row and the printed schedule must agree with the current KOPIS
title, venue, weekday and time. Only the named programme between the
exclusive composer credit and festival footer is considered.

The publisher checks the parent title against an independent composer's
catalogue and the live work list. Each excerpt must cite its parent and
its own printed number on the same line. Repeated arias from an opera are
separate programme items but count as one concert/work association. No
complete opera, edition, OCR confidence or other festival date is inferred.
Both authority documents, the original and the unchanged reading are kept
with the atomic publication history. Existing programmes are not replaced.
