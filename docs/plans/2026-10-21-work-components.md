# Work Components Implementation Plan

## Approved scope

The user approved the preceding diagnosis and design: preserve a collection and
its individual pieces as different works, link them, and remove misleading
partial-word search results. Audit all 11,646 current works, not only entries
without Korean titles. Do not claim universal coverage of classical music.

## Architecture

Reuse `works`, `work_aliases`, and the existing catalog `provider_records` for
additive, source-backed imports and explicit `work_component` relationships.
Publish a small versioned relationship registry for the web, derived from the
same guarded plan; do not expose the private provenance table. This avoids an
unrelated database permission/schema change. Validate both endpoints, composer,
ordinals, uniqueness and acyclicity before any import. A component is never an
alias of its parent. Unknown or conflicting identities stay in the audit.

New reference works retain review-only matching. Existing concert programs and
notifications are untouched; a parent performance never automatically implies
a specific component, and a component performance never implies the whole work.
The detail page provides links between verified parents and children separately
from directly matched performances. Search uses parent context to disambiguate
components, not to make a parent and child equivalent.

## Tasks

- [x] Audit current Wikidata entities and explicit part relationships, including
  linked missing children. Supplement source-observed named pieces from public
  bilingual recording metadata and verified program documents. Report every
  existing work's evidence/absence, without assuming missing claims mean no parts.
- [x] RED/GREEN: shared search rejects partial-token false positives and resolves
  a component with its parent/composer context. Preserve shorthand regression cases.
- [x] RED/GREEN: component importer validates identity, source, ordering, cycles,
  repeat execution and no modification of existing work/program records.
- [x] RED/GREEN: website loads verified relationships and shows parent/child links
  without inheriting concert availability. Cover unavailable/dangling metadata.
- [ ] Apply the guarded additive plan, read back every record, replay with zero
  additions, and compare all prior data. Publish full audit and source provenance.
- [ ] Run Python/shared/web tests, lint/build, corpus search checks and browser
  checks. Review sequentially in the main thread. Commit only task files, merge
  after CI, verify Vercel production and public artifact fingerprints.

## Acceptance cases

`고독한 꽃` identifies Schumann's third Waldszenen piece, not Waldszenen itself.
`슈만 숲의 정경 3번`, `Einsame Blumen`, and its observed English name find that
piece. Searching an unknown phrase containing `꽃` does not return unrelated
flower/fireworks works. Duplicate generic movement names remain disambiguated by
parent/composer; source-only imports cannot trigger automatic concert matching.
