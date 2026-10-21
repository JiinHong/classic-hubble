# Korean Work Names and Search Aliases

Continue the approved fixed-dictionary approach: Korean display titles from Korean
concert programs, search-only shorthand from observed audience usage. No LLM
translations, invented popularity ranking, new canonical IDs or automatic-match
promotion. This is a reviewed first batch, not complete Korean coverage.

- [x] Inspect existing catalog, source crosswalks and matching review guard.
- [x] Research official Korean programs and community naming examples.
- [x] Add a source-linked dictionary with stable QIDs and identity/old-title guards.
- [x] Write failing tests for guarded, additive, repeatable application and search.
- [x] Implement the importer and spacing-tolerant Korean search.
- [x] Run full tests, lint/build and a separate review pass.
- [x] Apply to Classic Hubble only; verify unchanged IDs/programs and rerun safety.
- [ ] Deploy and verify real Korean queries; record counts and limitations.

Nickname ambiguity remains a search concern: `비창` must retrieve both Beethoven's
sonata and Tchaikovsky's symphony. Bare composer-plus-number abbreviations such as
`라흐2` are excluded from this batch. Existing aliases are not deleted. Work aliases
may repeat across different works. Spacing variants are normalization, not claims
of independently observed community usage. Display-name curation is not verification
of imported work identity/catalogue completeness.
