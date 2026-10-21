# Program search evaluation

## Source candidates, not ground truth

`source-candidates.json` was exported read-only from the Classic Hubble database on 2026-10-21. It contains 30 distinct KOPIS performances with 119 stored NOL program text blocks, source URLs, and available KOPIS introduction-image URLs. Selection is deterministic by KOPIS ID, not a random or representative sample. Every record is pending manual annotation. URLs may change and text may contain several works or non-program content.

Do not use this file to claim OCR or work-matching accuracy. It contains neither image annotations nor an independently verified answer set. Source text remains attributed to the linked provider; do not redistribute provider images as a public dataset without checking the applicable permissions.

## Audit baseline

- 5,562 stored performances, including five legacy demo performances excluded from the public catalogue in this change.
- 224 real NOL program rows, all initially unlinked.
- Four canonical works, four composers in the canonical catalogue, 19 work aliases. The separate browsing composer directory is larger and is not the works catalogue.
- A dry run of `program-match` proposed zero matches across those 224 rows. This is not evidence of zero useful source information: the canonical catalogue is too small and many source blocks require extraction/splitting.
- Scheduled NOL enrichment had recorded hundreds of failures while the workflow still appeared successful. The worker now records the first NOL error and exits unsuccessfully on partial NOL failures while retaining successful KOPIS writes. A successful local `nol-check` does not establish hosted-runner reliability.

No production data was modified to obtain these measurements. Counts are a dated snapshot, not a live status page.

## Next implementation sequence

1. Inspect each source and annotate composer, work title, catalogue number, musical key, movement/excerpt scope, and exact source evidence. Distinguish absent programs, unreadable programs, and extraction failures.
2. Add verified canonical works and aliases through a reviewed seed/import. Include near-collision cases: shared surnames, reused opus numbers, movement-only entries, and multiple numbering systems.
3. Implement image/PDF text extraction with OCR. A text-only LLM may later propose structured fields, but must not invent DB identifiers or decide a match without evidence. Images are not sent to an LLM.
4. Compare rules-only and text-assisted extraction on held-out sources. Keep versions of the same poster and records from the same performance in the same split to avoid leakage.
5. Measure field-level precision/recall, canonical-link precision and coverage, abstention rate, processing cost/time, and change-detection false positives. Report the denominator and manual ground-truth procedure.
6. Connect unresolved results to a real protected review screen; publish approved changes and generate idempotent notifications only afterwards.

## Current boundaries

This delivery fixes catalogue truthfulness, pagination, current-date filtering, guarded DB-backed matching, and ingestion failure reporting. OCR, structured text extraction, expanded work coverage, real review actions, and notification delivery are not complete. Catalogue reads still load the whole server-side catalogue before filtering; a paginated search endpoint is the next scaling step. The current UI only renders 24 performance results at a time and allows loading more.
