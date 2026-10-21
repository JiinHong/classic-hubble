# Observed Korean and English Work Names

Continue the approved source-backed naming approach across the remaining catalog.
The user explicitly requests Korean and English names actually used by people.
Do not generate another translation batch or equate source presence with measured
popularity. Preserve canonical IDs, programs, existing names and review-only status.

- [x] Inspect missing coverage and Korean work-list / English article sources.
- [x] Add failing tests for language-aware evidence imports and ambiguous identities.
- [x] Extend the existing guarded importer and Wikipedia collector for English names.
- [x] Extract Korean work-list names only where a unique composer/catalogue identity
  and compatible work scope can be established; retain rejected rows for review.
- [x] Collect and audit actual source data; preserve revision URLs and raw evidence.
- [x] Run full tests and a separate same-thread review, then apply and verify DB diff.
- [ ] Publish source attribution, deploy, and test Korean/English searches in production.

Implementation uses Python/httpx and existing source crosswalks. English titles stay
canonical display values; alternate English forms become aliases. New Korean
source titles fill missing values, without overwriting previously chosen names.
Wikipedia section redirects, ambiguous codes, arrangements and collection excerpts
must not silently become aliases for another work. Every count distinguishes
observed names from previously generated formal renderings.
