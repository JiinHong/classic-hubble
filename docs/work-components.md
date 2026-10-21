# Work components

## Scope and evidence

The 2026-10-21 inventory checks all 11,646 existing works, 427 additional
Wikidata entities, and 334 bilingual public album pairs. It selects 789 new
component works, 880 aliases, and 1,368 parent-child relationships across 429
parents. These are source-bounded counts, not a claim to cover every component
of every classical work. An absence of evidence is not evidence of no parts.

The public `reference/work-component-audit.json` records a decision for every
existing work and the accepted relationships. The import manifest in
`workers/data/work-component-inventory.json` retains source evidence and its
content digest. Imports archive that manifest to R2 and verify the readback
before touching the database.

Wikidata relationships require explicit part claims and compatible work types
and composers. New album-only components require agreement between two distinct
album IDs, not merely two language versions of one album. Explicitly reviewed
primary program documents can also establish identities and positions.
Conflicting positions, combined movements, arrangements, ambiguous existing
identities and insufficiently corroborated titles remain held for review.

Schumann's `Einsame Blumen` is independently represented as `고독한 꽃`, the
third piece of `Waldszenen` (`숲의 정경`). Its Korean name and position are from
the 2020-11-04 Cho Seong-Jin recital program published by Credia:
https://crediamusic.wisacdn.com/news/programbook/CSJ_PROGRAM_SAC-ARCHIVE.pdf

## Search and display

A component is not an alias of its parent. Search considers its own names plus
its parent's name, aliases, catalogue and explicit component number. All query
tokens must match; a single matching word cannot produce unrelated results.
Cards show the parent and position below the title. Detail pages link to the
parent and its other verified components.

Concert availability is never inherited in either direction. New reference
works use the existing review-only matching policy, including `component-`
slugs, and cannot automatically publish program items or send notifications.

## Deployment and repeat execution

1. Run worker, shared and web tests, lint, build and catalog search regressions.
2. Deploy the `component-` review-only guard to both the GCP collector and the
   GitHub main branch before importing any new rows.
3. Deploy the web relationship registry generated from the same manifest.
4. Dry-run the import against the explicitly named project:

```sh
.venv/bin/python -m classic_hubble_pipeline.component_import \
  --manifest workers/data/work-component-inventory.json \
  --project-ref klnfamtwxwrelrjeguqb \
  --report /tmp/work-components-dry-run.json
```

5. Add `--apply` only after confirming the target and held count. The importer
   adds works, aliases and provenance records with deterministic identities;
   it does not modify prior work titles, program items or notifications.
6. Read back all accepted records, compare prior works and program items, and
   rerun the dry-run. It must plan zero new works, aliases and relationships.
7. Verify production searches, parent/child navigation, mobile layout and the
   published audit digest.

Partial write failures are recoverable by rerunning the same verified manifest.
Do not substitute a newly generated manifest during recovery. The web omits
relationships whose endpoints are not yet present; database additions do not
imply atomic publication of the entire registry.
