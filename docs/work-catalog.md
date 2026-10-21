# Canonical Work Reference Catalog

## Scope and source

The 2026-10-21 snapshot queries Wikidata for the 220 composers already identified
in the reviewed composer directory. It contains 16,952 unique source items.
The production import accepts 11,646 works and reuses the four curated work IDs:
11,642 new works and 205 new composers, giving 209 composers with eligible works.
These are reference records, not 11,646 manually verified compositions, a complete
history of classical music, or a claim that each work has an upcoming concert.

The conservative filter excludes 5,306 items: 4,461 without an English label,
621 with additional/noncanonical type declarations, and 224 with ambiguous or
unsupported composer identities. This intentionally omits some valid music.
Of the new records, 4,342 have a recognized catalogue number and 717 have a
source-provided Korean title. Missing metadata remains missing. Original labels,
all raw catalogue statements and exclusions remain in the snapshot.

- Wikidata structured metadata is [CC0](https://www.wikidata.org/wiki/Wikidata:Licensing).
  Its [query service](https://query.wikidata.org/) is the source of this import.
  It is collaboratively edited, not a universal scholarly authority.
- [Open Opus](https://openopus.org/) is a useful classical reference catalog and
  the existing composer-directory source. Its works API timed out during this
  investigation; no Open Opus works were imported.
- The [Koechel catalogue](https://kv.mozarteum.at/en) and
  [Beethoven-Haus work archive](https://www.beethoven.de/en/work/search) are
  composer-specific scholarly verification sources. They were not bulk imported;
  public visibility does not establish a reusable bulk-data license.

## Import contract

Run from the repository root with the worker environment installed:

```sh
python -m classic_hubble_pipeline.catalog_import fetch --directory /path/to/snapshot
python -m classic_hubble_pipeline.catalog_import import \
  --snapshot /path/to/snapshot/snapshot.json --report /path/to/dry-run.json
python -m classic_hubble_pipeline.catalog_import import \
  --snapshot /path/to/snapshot/snapshot.json --report /path/to/applied.json --apply
```

`fetch` queries ten composers at a time, caches successful responses, pauses between
requests and stops on provider errors. `import` is a dry run unless `--apply` is
present. Supabase and, for apply, private R2 credentials come from the ignored
`.env`; they are never included in reports. Check the report's target URL first.

Before database writes, apply archives the complete snapshot under
`catalogs/sha256/...` in R2 and reads it back to verify integrity. Each imported
work has a Wikidata QID crosswalk and raw source record in private
`provider_records`. The report records the private archive key and object hash.

IDs derived from QIDs, conflict-ignoring inserts and unique aliases make a rerun
safe after a partially completed batch. The import is not one atomic transaction.
It never overwrites local titles, deletes works, updates concert programs or
creates notifications. A later upstream correction needs explicit review rather
than silently replacing curated information. Never delete a source snapshot as
part of rerunning an import.

## Matching and publication

Imported references are searchable and can be saved by users, but are review-only
for automatic program matching. The imported slug enforces this even if a run
stops before inserting aliases. Legacy works with curated aliases keep their
existing matching eligibility. There is no bulk promotion-to-curated workflow yet.

The matcher compares composer identity, catalogue number, title and available key
or work-number evidence. `Op. 27/2` must not match `Op. 27`; a range is not a single
work. K and KV are equivalent only in combination with composer and number.
Catalogue numbers can describe collections; movements, arrangements, conflicting
editions and source mistakes still need review. Exact identifiers are not proof
of semantic correctness.

The intended pipeline is grounded OCR text -> constrained text-LLM extraction ->
local candidate retrieval -> deterministic conflict checks -> confirmed link or
review. LLM output cannot create a trusted work ID or invent missing facts. The
text LLM is not connected yet. No 100% recognition or matching-accuracy claim is
made; measure precision and coverage on separately annotated programs first.

## Search limits

The web catalog reads beyond Supabase's 1,000-row page limit with bounded
concurrency. Unranked works remain searchable, and unknown ranks are not shown as
invented rankings. Work cards display in batches of 24 while searching the full
catalog. The client still receives the catalog for local search; server-side
search/pagination is a later scaling task, not completed by this change.

## Deployment order

Deploy the review guard and pagination/search corrections before applying the
snapshot. Verify the four original works, their 19 curated aliases and all
program links remain unchanged, then run a second dry run to confirm zero new
work/composer inserts. Record actual production counts separately from dry-run
counts. The GCP KOPIS collector does not run NOL enrichment; any process running
matching must use this guard before imported references are available.

## Production verification, 2026-10-21

Applied at 04:55:45 UTC after production commit
`b52813a2657098dece91b4449cf49e4e880b23c8` became ready (PR #7).
Read-back counts: 209 composers, 11,646 works, 21,566 title/alias rows and
11,646 private source crosswalks. Of the works, 4,346 have a parsed catalogue
number and 721 have a source/local Korean title. All 11,642 new works are
review-only. These counts include collections or excerpts where Wikidata models
them as compositions; they do not assert a uniform whole-work level.

The original four composer/work rows, 19 curated alias rows and all 229 program
items compare identically with the pre-import snapshot. Real matcher checks
preserve the curated Beethoven fifth symphony link and return only a review
candidate for the newly imported *Fuer Elise*. A second dry run proposes zero new
composers or works. Missing Korean labels and instrumentation are not fabricated.

Snapshot digest:
`c4173d0c866b2bf95cbebd2be00bb3151b669534d499fcd523fe461daa7107c9`.
Private R2 bucket: `classic-hubble-sources`. Object key:
`catalogs/sha256/76/76071786b32938ce4817b512d135742e481d8fbcde5a838e878c51a182c54f6c`.
A private `wikidata/catalog_snapshot` provider record stores the archive pointer
and verification receipt. This receipt was recorded during operational rollout;
the CLI itself writes the detailed local report and per-work crosswalks.

Production UI verification found 11,646 searchable works; Korean search for
*Fuer Elise* returned its new record, with WoO 59 and the Wikidata source on its
detail page. The narrow in-app viewport displayed it without overlapping text.
Home returned HTTP 200 in 10.59 seconds with 6,697,841 uncompressed bytes, versus
10.93 seconds and 725,779 bytes before import. These are single observations, not
a performance benchmark. Initial transfer size and full-catalog reads remain
known scaling work. No error/fatal runtime logs appeared during this smoke check.

Local and PR CI verification: 289 Python tests, 81 shared/web tests, ESLint and
the production build passed. These tests verify implementation behavior, not
measured real-world OCR or music-identification accuracy.
