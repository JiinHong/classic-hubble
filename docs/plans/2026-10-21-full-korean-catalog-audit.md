# Complete remaining-work naming pass

Process the 8,442 works that have no Korean display title at the start of this
run. Finish research, conservative application, verification and deployment in
one run. No invented Korean title, inferred nickname, or automatic identity
promotion is allowed.

Research every target through its canonical Wikidata ID, including Korean and
English names, Korean article links and explicit external work identifiers.
Follow available Korean reference/recording work links and compare bilingual
metadata and composer identity. Reuse the earlier source corpus as additional
evidence, not as a claim that the entire web was searched. Record the sources
actually checked per work and distinguish missing names, conflicting identities
and unavailable sources. "No name found" always means within those sources.

Use the existing guarded naming importer for accepted names. Persist an audit
record for every target in provider_records and publish a non-sensitive audit
file. Preserve canonical IDs, previous names, aliases, programs and review-only
status. Do not change the database schema or infer catalogue fields from names.

Implement parser/audit behavior with tests first. Verify target-set equality,
source traceability, no unintended updates, repeat application, full-catalog
search, local tests/build, CI and the production site. Reviews run sequentially
in the main thread under the user's AGENTS instructions. Exclude docs/capstone/.
