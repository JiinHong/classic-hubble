# Recording-catalog name enrichment

Continue the source-backed Korean catalog enrichment from 2,390 named works
and 9,256 unnamed works. This is a naming-data change, not concert publication.

1. Read public album work headers in Korean and English, with cached,
   sequential requests. Do not request audio, private APIs, or blocked paths.
2. Test extraction before implementation. Pair names only by the same public
   work and composer identities; never inherit a track title from its group.
3. Require a unique composer/catalogue match and check key, ordinal, and scope.
   Keep ambiguous or conflicting candidates in an audit rather than inventing
   translations. A source occurrence is evidence of usage, not popularity.
4. Produce a new immutable manifest and attribution dataset. Preserve existing
   Korean names, aliases, canonical identities, and review-only status.
5. Test, dry-run against a fresh database snapshot, apply, verify readback and
   idempotence, then release through CI and verify production search.

Reviews run sequentially in the main thread as requested in AGENTS.md.

Progress: research, extraction tests, manifest review, dry-run, production apply
and readback are complete. The batch adds 814 titles and 2,567 aliases; 8,442
titles remain unresolved. All 977 provenance records and replay idempotence are
verified. Forty-eight full-catalog searches pass after test-first fixes for
numeric-prefix matching and explicit catalogue subnumber ranking. CI release
and production browser verification remain.
