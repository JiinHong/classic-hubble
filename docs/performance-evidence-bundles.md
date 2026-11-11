# Performance Evidence Bundles

## Problem and scope

The cached 773-image cohort represents 511 performances, not 773 performances.
The prior 44 / 353 / 114 performance breakdown mixed successful identity
recognition with publication constraints. Multiple images and non-full-work
scope were blanket publication blockers even when identity was well supported.

This change implements the user's approved performance-level evidence and
separate-extent design. It does not run new OCR or automatically add unverified
catalogue entries. A work identity is not evidence that its whole work was played.

## Publication contract

Call `paddle_publication.publish_bundle(repository, store, client,
performance_id, review_ids, apply=False)` with the saved selections for **every
current intro image**. A single-image performance uses the same contract.
Change `apply` to true only after the migration and UI are deployed.

The one-performance command is dry-run by default (DB/R2 reads, no OCR or model
calls). Supply the saved review ID for each unique current image hash:

```sh
python -m classic_hubble_pipeline.paddle_publication --performance-id PERFORMANCE_UUID --review-id COVER_REVIEW --review-id PROGRAM_REVIEW
```

Add `--apply` only for a deliberate public write. It rechecks live originals and
uses the atomic bundle RPC. Do not infer completeness from a `ready` dry-run;
current DB checks and live source verification occur on apply.

- Existing immutable `paddle-partial-program-v1` reviews retain their provenance.
- New publication version: `paddle-performance-bundle-v2`.
- Only single-day performances are currently supported.
- At least one high-quality image date must match the performance. Another
  current image may supply the program without repeating that date.
- By default, a conflicting, invalid, or unsupported date blocks the bundle.
- Every image needs a saved selection. `no_program_identified` is explicit
  reviewed absence; `uncertain` is not and blocks a complete bundle.
- Every original and OCR document hash is verified. Every live image is checked
  before applying. SQL rechecks the exact performance, archive, latest OCR and
  immutable review pointers together. Newer or tied competing OCR is stale.
- Only explicit-composer, exact catalogue/alias identities with program context
  and cited OCR scores >= 0.9 are eligible. This is not an accuracy claim.
- Known identities may carry `full_work`, `movement`, `excerpt`, `arrangement`
  or `unknown`. Scope and literal movement text are stored separately and shown
  on the site. Historical NULL scope is not relabeled as full work.
- Derived references need their own reviewed selection and remain withheld.
- Duplicate identity/scope/detail observations are coalesced, retaining every
  reviewed document in private publication history.
- Manual, NOL and other providers are protected. A smaller new subset cannot
  silently erase an earlier linked identity. Such cases require explicit review.
- The performance remains `partially_confirmed`; no entire-program claim.

The old single-image `publish` / SQL RPC remains compatible for existing
full-work-only callers. New performance-level callers must use `publish_bundle`;
do not loop the old API once per image and call that bundle validation.
The compatibility RPC preserves performances that already have scoped bundle
rows, preventing older workers from replacing them with a full-work-only subset.
Its previous implementation is retained as `publish_paddle_program_v1`; future
contract changes must account for both entry points.

### Dated programmes on the same poster

For a reviewed **single-image, single-day concert**, pass `--dated-program`
to require a programme section for that day. The opt-in proof currently accepts
two consecutive, weekday-labelled Korean dates on separate rows beneath one
programme heading, in a single centered column. A reliable cover date supplies
the year, and an explicit artist heading closes the programme. Both the current
OCR bytes and the citation positions must agree with the stored original. A
date elsewhere on the poster, a sale date or an item in the artist biography
cannot supply programme evidence. Other layouts remain private.

The same restricted SQL function locates the section for preview and recomputes
it under the publication lock. All cited composer, title, catalogue, key and
movement spans must be inside its boundaries and meet the existing OCR quality
threshold. Other dates can be present in the saved review; their items are
withheld, not renumbered or copied. The private receipt retains the original
review and OCR identities and the proof's line positions, not a second copy of
the entire OCR document. A dated publication never confirms the full programme.

A numbered selection can identify a collection without identifying a complete
performance of it. The first supported authority is [Poulenc's fifteen piano
improvisations](https://catalogue.bnf.fr/ark:/12148/cb139840284). The exact
composer and title lines must be adjacent inside the date section, and each
printed range must also be cited in the saved selection. Numbers wholly within
the overlapping ten-piece set stay unresolved. Separate selections retain their
own positions and literal ranges, even if both point to the same work. A later
subset cannot erase a previously published excerpt with explicit scope details.

## Matching and reads

A composer-family surname plus a composer-specific catalogue and a named title
can enter the existing catalogue matching checks. Generic Op./WoO numbers and
bare catalogue-only titles do not resolve ambiguous composers. Title, number,
key, instrument and duplicate-catalogue checks still apply.

Bundle validation loads the catalogue once and requests OCR pointers only for
the current source hashes and bucket. It does not scan the global OCR/archive
tables. The final transaction uses current pointers, not cached eligibility.

## Release and remaining cases

Apply `20261028071051_publish_performance_evidence_bundles.sql` before deploying
the web query that selects the added columns. Run the rollback-only SQL test
`supabase/tests/paddle_bundle_publication.sql` against the target schema before
publication. The function is service-role-only and security invoker.

Unit tests cover cross-image dates, scopes, missing/uncertain selections,
stale originals, ambiguous composers, low evidence and bounded reads. The SQL
test covers grants, scope/source tampering, dates, stale OCR, idempotence,
history and manual preservation. Offline eligibility replay is diagnostic only;
it cannot confirm current-source validity or count actual public additions.

Still not automatically resolved: conflicting/multiple concert dates, genuinely
unreadable or absent programs, ambiguous/composerless titles, missing canonical
records without authoritative evidence, and derived subitems without a saved
selection. False date-heading cases such as a season or award name require a
separate regression-backed date contract update, not a blanket warning bypass.

### Direct programme sheets corroborated by KOPIS

`vision_publication.publish_kopis_sheets` is an explicit, single-date path.
The dated cover and first programme header must identify the same concert
and venue. Later sheets need not repeat the date, but every original must
have a complete, immutable direct reading. The typed KOPIS programme must
agree on every credit, work, composition year, instrumentation and running
order. Catalogue titles or source-verified aliases must independently resolve
both spellings to the same unique work. Programme text cannot replace a
missing original, and the path never infers that a work was played in full.

A preview leaves the database unchanged. Applying it checks the current
bytes of every original and revalidates the entire packet inside one
transaction. Existing programmes are preserved; an identical published
bundle is a no-op. The private audit retains the individual sheet provenance
and the exact typed KOPIS lines. The rollback-only contract tests are in
`supabase/tests/direct_kopis_sheet_bundle.sql`.

### Direct readings with printed movements

`direct_movement_publication.publish` associates only the dated programme's
printed movements with their parent work. It keeps the exact movement text
and does not reinterpret a list starting at I as a complete performance.
The single current image, stored direct reading, KOPIS date, start time and
venue must agree. Both the frozen match and a new catalogue match must have
the same unique composer and work number; the database checks the current
catalogue again under lock. A year, booking date, title alone or performer
credit cannot authorize a publication. Unsupported items stay private, and
the concert remains partially confirmed. The ordinary direct publisher
cannot replace these scoped rows. See `supabase/tests/direct_movement_program.sql`.

### Independent parent-work evidence

An optional direct-reading replay can recover a printed parent work that did not
exist in an older match snapshot. It does not overwrite that snapshot. A private,
content-addressed catalogue record identifies the edition-neutral parent, its
composer and its literal title using a named authority. This is never a source
for the concert programme. The worker checks its R2 bytes and the database checks
its digest, the current canonical row and possible conflicting identities again.

The concert still needs one current sheet with the same official date, time and
venue. A previously empty match needs a unique present-day catalogue match,
literal title, key, number, credited composer and cited movements. A title-only
work needs the same unambiguous full-work identity in both match snapshots.
Both publish only the association with unknown extent, retaining any movements
as printed. An identified arrangement, changed credit, conflicting candidate or
claimed edition is held. Existing concert links are never overwritten.
