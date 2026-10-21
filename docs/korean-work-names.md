# Korean Work Names and Aliases

`workers/data/korean-work-names.json` is the first reviewed batch of 35 works.
Display names follow Korean concert programs from presenters such as Seoul Arts
Center and the Seoul Philharmonic. Search aliases additionally use observed
audience shorthand in GoClassic, DC Inside, concert reviews and music publications.
Every chosen title/alias links to its source. These examples establish usage, not
measured popularity or complete coverage of the 11,646-work reference catalog.

Examples include `라흐 피협 3번`, `베피협5번`, `브피협2번`, `차바협`, `멘바협`,
`즉흥환상곡` and `골드버그 변주곡`. Spacing and the ordinal prefix `제` are
editorially normalized; normalized variants are not separately observed usages.
Search normalizes Korean spacing and composed/decomposed Hangul. Composer and
title tokens can jointly raise a result's rank. This is retrieval, not proof of
work identity: `비창` intentionally retrieves both the Beethoven sonata and the
Tchaikovsky symphony. Unqualified composer-plus-number abbreviations such as
`라흐2` are not added by this batch. Earlier aliases remain untouched.

## Applying a reviewed batch

Run from the repository root with the worker environment installed:

```sh
python -m classic_hubble_pipeline.korean_work_names \
  --dictionary workers/data/korean-work-names.json --report /tmp/korean-names-plan.json
python -m classic_hubble_pipeline.korean_work_names \
  --dictionary workers/data/korean-work-names.json --report /tmp/korean-names-applied.json \
  --apply
```

The default is read-only. The command checks the Classic Hubble project URL, QID
crosswalk, composer identity, English title and previous Korean title before
writing. New aliases and source evidence use conflict-ignoring inserts. Title
updates compare the old value at write time and stop on concurrent edits. The
report preserves the target work/alias rows before application; protect it like
an operational backup. A batch is not atomic, but a partial run can be repeated.

Only `works.title_ko` is updated. IDs, slugs, English titles, catalogue numbers,
composers and concert links are unchanged. Old Korean titles become aliases.
Private `provider_records` evidence contains the dictionary version, digest and
source links. `ko-usage:` aliases are not `curated` matching evidence; imported
works remain review-only. Naming review does not resolve incomplete catalogue
numbers, editions, arrangements or other source identity errors.

For a later batch, record each target's current Korean title as
`previous_title_ko`, verify its existing source crosswalk and test a dry run before
application. Never relax an identity guard merely to make an import succeed.

## Production data verification, 2026-10-21

Applied 17 Korean title changes and 55 new title/alias rows across 35 reviewed
works. Total counts are 209 composers, 11,646 works, 21,621 aliases and 229 program
items. Korean-titled works increased from 721 to 723: most of this batch improves
existing names and adds audience search terms, rather than translating previously
unnamed works. All existing aliases and all work fields except the intended Korean
titles and their update timestamps compare unchanged against the pre-apply backup.
Composers and program items compare identically. All 11,642 imported works remain
review-only; the four curated works retain their matching eligibility.

A second dry run proposes zero title changes and zero aliases. All 35 evidence
records were read back. Searching the complete production catalog locally places
the expected work first for ten queries, including spaced shorthand, composer plus
`비창`, `차바협`, `멘바협`, `즉흥환상곡` and `골드버그변주곡`. Bare `비창`
retains both works. This checks retrieval behavior, not corpus-wide relevance.

Verification: 302 Python tests, 84 shared/web tests, Ruff, ESLint and Next.js
production build. An existing login test intermittently clicked while the button
was disabled; it now waits for authentication initialization, without changing
login behavior. Review was performed sequentially in the main task, not by an
independent agent. Browser/deployment verification is recorded with the release.

## Catalog-wide expansion, 2026-10-21

The first 35 works are a reviewed starting batch, not the coverage target. Two
additional, independently labelled datasets expand the existing catalog:

- `workers/data/korean-wikipedia-names.json`: 688 identity-bound Korean Wikipedia
  articles, with 1,634 title/redirect strings. Applying this adds 915 alias rows
  across 609 works. These include spelling, spacing, ordinal and disambiguation
  variants; they are not 915 distinct audience nicknames or popularity claims.
- `workers/data/korean-formal-names.json`: 1,661 strictly supported English formal
  titles rendered with 18 established Korean genre terms, ordinals and keys.
  Applying this fills 1,338 missing Korean titles and adds 1,654 alias rows.
  Catalogue suffixes are retained. Unknown forms, movement suffixes, arrangements
  and programmatic names are not translated. Existing Korean titles are preserved.

Wikipedia article QIDs must match the existing work crosswalk. A title alone never
selects an identity. Incoming redirects to a section are excluded, so a name for
one movement does not become an alias for the whole work. Revision URLs, page IDs
and incoming redirect observations are retained as evidence. Redirects describe
the collection-time state, not necessarily the linked historical revision.

The formal renderer's bilingual term examples are checked against the reference
data. They establish genre terminology, not observed usage for every generated
title. These aliases carry `ko-form:` and `formal_rendering_only`; Wikipedia names
carry `ko-wikipedia:`. Neither prefix upgrades imported works to verified matches.
No LLM-generated nickname or guessed composer-plus-number shorthand is added.

After both imports: 1,960 distinct works have new names/aliases; Korean-titled works
increase from 723 to 2,061 (17.7% of 11,646). Alias rows increase from 21,621 to
24,190. This remains partial Korean coverage: 9,585 works have no Korean display
title. All composers, all 229 program items, previous aliases and non-title work
fields compare unchanged against the pre-import backup. All 11,642 imported works
remain review-only. Evidence for all 2,349 dataset entries was read back.

### Reproducing and applying the datasets

Obtain Korean Wikipedia sitelinks from the Wikidata query service as SPARQL JSON:

```sparql
SELECT ?work ?article WHERE {
  ?article <http://schema.org/isPartOf> <https://ko.wikipedia.org/>;
           <http://schema.org/about> ?work.
  ?work <http://www.wikidata.org/prop/direct/P86> ?composer.
}
```

The collector intersects those IDs with the actual Classic Hubble catalog before
requesting article names. Requests use batches of 50, API continuation, a one-second
delay and cached responses. API errors stop the run rather than implying an empty
successful result. Generate new candidate files rather than overwriting an applied
manifest, whose digest and previous-title guards form its audit record:

```sh
python -m classic_hubble_pipeline.wikipedia_work_names \
  --sitelinks /tmp/ko-sitelinks.json --cache /tmp/ko-wiki-pages \
  --output /tmp/ko-wikipedia-candidate.json \
  --formal-output /tmp/ko-formal-candidate.json \
  --public-output /tmp/ko-public-candidate.json
```

Inspect the candidates and assign a new version for a later batch. Apply each
dictionary with the guarded `korean_work_names` command above, first without
`--apply`. Reads are bounded to 100 IDs per request; inserts are conflict-ignoring
and display updates compare the previous value. Both applied manifests are tracked
in Git. Public names, source URLs and licensing are available at
`/reference/korean-work-names.json`; operational IDs and previous-title guards are
excluded. The footer links this evidence and the Wikipedia CC BY-SA attribution.

### Search shorthand and ambiguity

Search expands observed genre shorthand (`피협`, `바협`, `피소`, `현사`), including
glued inputs such as `모차르트피협21번`. This is a retrieval rule, not thousands of
individually sourced DB aliases. `피소` and `현사` have direct usage examples in
[GoClassic piano discussion](https://www.goclassic.co.kr/club/board/viewbody.html?code=letsplay&go=&group=43&number=50)
and [GoClassic chamber discussion](https://m.goclassic.co.kr/club/board/viewbody.html?code=chamber&go=&group=3368&key=&keyfield=&number=9772&page=121).
The first reviewed dictionary retains per-work sources for `피협` and `바협`.

Number tokens match whole ordinals: `4번` does not count as `14번`. When results
cover the complete query, partial-only matches are omitted; otherwise the previous
partial-match fallback remains. Bare `비창` still returns both relevant works.
Short composer prefixes can remain ambiguous; search never merges their IDs.

### Verification and review

Both post-apply dry runs propose zero titles and zero aliases. Thirteen asserted
queries against the full production catalog cover formal names, glued shorthand,
ordinal isolation and the two distinct `비창` identities. `차바협` ranks the expected
work first but retains eight prefix-compatible results; `멘바협` retains two.
These checks do not establish corpus-wide search accuracy.

Verification: 333 Python tests, 12 shared tests, 76 web tests, Ruff, ESLint and the
Next.js production build pass. The new tests were observed failing before their
implementation. A full-catalog probe caught partial genre matches crowding exact
composer/number queries; regression tests cover the corrected behavior.

The final diff was reviewed sequentially in the main task for source identity,
concurrent-update guards, repeat application, provenance, public-data scope and
search regressions. A simplification pass retained the existing importer and
removed formatting noise without broad refactoring. No independent-agent review
was performed: the user's task instructions require same-thread execution, which
does not satisfy the independent-review skill's dispatch contract. Browser and
deployment checks are recorded with the release.
