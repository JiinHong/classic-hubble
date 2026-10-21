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

## Observed Korean and English expansion (2026-10-21, second pass)

This pass adds source-observed names, not another formal-translation batch:

- `english-wikipedia-names.json`: 4,596 exact-QID works, 16,343 observed article
  titles/redirect names before deduplication against the database. Fragment redirects,
  missing pages and disambiguation pages are excluded. English aliases never write
  a Korean display title, including when a later Korean curation has changed it.
- `korean-worklist-names.json`: 386 works from 11 Korean composer/work-list pages.
  The candidate review fills 128 missing Korean display titles. Complete catalogue
  codes and composers must match uniquely; duplicate codes, conflicting rows,
  incompatible genres, work numbers, keys and excerpt scopes are excluded.
- `concert-usage-names-2026-10-21.json`: six works checked against concert programs
  and concert notices. Adds variants such as `홀베르그 모음곡`, `다비드동맹무곡`,
  `포욜라의 딸`, `목신의 오후 전주곡`, and `터키풍` to their own work IDs.
  The two new preferred titles do not overwrite any pre-release Korean title.

These are **observed usages, not a measured popularity ranking**. The first 35-work
curated dictionary remains intact. Wikipedia provides broad reference coverage;
concert/community evidence is recorded separately. No invented abbreviations are
created by combining composer initials, genres and arbitrary numbers.

`worklist-name-review.json` records manual exclusions and exact-substring trims.
`korean-worklist-rejections.json` retains 571 excluded candidate rows with reasons.
Examples include a source calling Mozart K.452 a quartet instead of a quintet,
Prokofiev Op.84 being labelled B-flat minor rather than B-flat major, and an
uncorroborated Sibelius transliteration. Beethoven Op.132's movement nickname is
removed from the whole-work title. Two concert-notice sources returned 403 on direct
fetch; their search-index evidence is explicitly labelled, not represented as a
successful direct-page retrieval.

### Collection and replay

Use the sitelink query above with `https://en.wikipedia.org/` and run:

```sh
python -m classic_hubble_pipeline.wikipedia_work_names \
  --language en --sitelinks /tmp/en-sitelinks.json --cache /tmp/en-wiki-pages \
  --output /tmp/english-names-candidate.json
```

Language is included in response cache identity. Article requests remain batched,
cached and rate-limited; no audio, video or personal data is collected.

`worklist_names.extract_rows` reads rendered MediaWiki parse responses, separating
table cells and direct list-item text from nested movements. `match_rows` produces
accepted/rejected candidates. `build_manifest` accepts those source documents plus
the explicit review decisions, works, composers and canonical crosswalks. Its output
must be inspected before use; source text is not an instruction to publish.
The committed source revision IDs and row evidence permit an independent recheck.

Replay the three new manifests in the order listed above with the guarded
`korean_work_names` importer, first without `--apply`. They are additive and use the
existing project restriction, identity guards and compare-and-set title updates.
The same importer can replay the old Korean-only manifests unchanged.

The public evidence file now includes both languages and the additional concert
sources. It exposes no operational UUIDs or previous-title guards. The footer
attributes both Korean and English Wikipedia contributors.

### Review and verification limits

Review was performed sequentially in this task, not by an independent agent, in
accordance with the user's AGENTS instructions. Whole-repository Ruff currently
reports 27 pre-existing findings outside this change; scoped Ruff for all changed
Python modules/tests is clean. Existing unrelated files were not reformatted.
Corpus-wide matching accuracy and popularity have not been established by this
name-enrichment pass; imported canonical works retain their review-only status.

### Verified database result

The production readback confirms 11,837 new aliases (363 Korean, 11,474 English)
across 3,939 changed works and 130 newly filled Korean titles. Totals are 36,027
aliases and 2,191 Korean-titled works out of 11,646 canonical works. The remaining
9,455 works still need Korean title research; source observation does not prove
that each spelling is frequent or preferred by audiences.

All 209 composers, 229 program items, canonical crosswalks, prior aliases and
non-title work fields were preserved. All 11,642 imported review-only works retain
that status. Every one of the 4,988 provenance records was checked, and replaying
all three manifests proposes zero title or alias changes.

Twenty-five searches against the full production catalog pass, including
`다비드동맹무곡`, both `홀베르그`/`홀베르크` spellings, `포욜라의 딸`,
`Rach 3`, `Emperor Concerto`, `Archduke Trio` and `Kreutzer Sonata`.
The two distinct works called `비창` remain separate. Verification also passes
348 Python tests, 12 shared tests, 76 web tests, scoped Ruff, ESLint and the
Next.js production build. This is sampled search verification, not a claim of
100% matching accuracy.

## Remaining-catalog continuation (2026-10-21)

This pass examined Korean reference pages for the represented composers and their
linked work lists (204 source documents), plus 613 public bilingual programme
labels in the KBS Digital K-Hall archive. It collects names, not video media.
The reviewed manifest is `workers/data/korean-catalog-continuation.json`, version
`2026-10-21.continuation.1`. It covers 375 works; 373 receive a new title or alias,
and two receive additional evidence without changing their existing names.

Source-list parsing now recognises Korean opus notation, explicit parent-list
genres and paired title/key table columns. Complete subnumbers remain part of
identity: Op. 8 and Op. 8 No. 12 are not interchangeable. Public archive labels
are checked for incompatible bilingual numbers/instruments and for excerpts,
movements or suites that must not become aliases for a complete parent work.
The archive parser processes supplied HTML; this change does not schedule a new
automatic crawler or publish unreviewed future candidates.

Reviewed concert and usage evidence takes precedence for new display names:
`엘레지` (Faure Op. 24), `핑갈의 동굴` (Mendelssohn Op. 26), and
`불꽃을 향하여` (Scriabin Op. 72). Their evidence is recorded in
`concert-continuation-review.json`. Wikipedia names remain source-observed
reference names, not measured claims of audience popularity. Unverified
translations and guessed shorthand are not added.

`korean-continuation-rejections.json` records 1,156 work-list and 344 archive row
rejections. These are rows, not distinct works. Examples include contradictory
Alpine Symphony/Aus Italien bilingual labels, a flute/violin concerto mismatch,
individual sarabandes from complete Bach suites, and an extracted suite from
The Miraculous Mandarin. The separate review files retain exclusions and exact
source-text trims. The public evidence file now has six datasets and retains
source URLs, Wikipedia revision/license details and short factual name evidence,
without operational UUIDs or previous-title update guards.

### Verified production result

- 199 previously missing Korean display titles filled; all 2,191 earlier titles
  preserved. Coverage is now 2,390 of 11,646 works, with 9,256 still unresolved.
- 496 aliases added: 427 Korean and 69 English. Total aliases: 36,523.
- All 209 composers, 229 program items, canonical crosswalks, prior aliases and
  non-title work fields unchanged. All 11,642 imported review-only works remain so.
- All 375 provenance records verified against the immutable manifest digest.
  Replay proposes zero title or alias changes.
- 38 sampled searches pass against the full production catalog. Both Schumann's
  and MacDowell's works named `숲의 정경` remain distinct. Composer-qualified
  queries also work when the Korean title token is typed without spaces.

The full-catalog search probe exposed a spacing bug: `슈만 숲의정경` could rank
unrelated Schumann works ahead of the requested work. A failing regression test
preceded the fix. Korean-only query tokens now tolerate spacing within candidate
names; Latin identifiers and exact numbered-work matching keep their prior rules.

Verification passes 363 Python tests, 13 shared tests, 76 web tests, scoped Ruff,
ESLint and the Next.js production build. Review was sequential in the current
task, not independent-agent review. This batch does not establish corpus-wide
matching accuracy or complete Korean-name coverage. The remaining 9,256 works
need further source research; titles were not translated merely to fill blanks.

## Recording-catalog continuation (2026-10-21)

This pass reads public Korean and English Apple Music Classical album work
headers: 47 albums, 94 cached HTML pages, 1,796 paired rows and 1,464 distinct
work headers. The accepted manifest uses 92 source pages. Names are paired by
public work and composer IDs, not album position or track grouping. No audio,
artwork, private API or search endpoint is collected. These are observed names,
not audience popularity measurements or invented translations.

`workers/data/korean-recording-names.json`, version `2026-10-21.recordings.1`,
contains 977 works with source URLs, fetch dates and content hashes. The existing
guarded importer applies it; do not edit an applied manifest. The accompanying
`korean-recording-rejections.json` records rejected candidates. Existing Korean
display names are preserved. New titles combine the observed primary Korean name
with the work's existing canonical catalogue; aliases retain the primary observed
Korean and English names.

Acceptance requires a unique composer/catalogue match plus consistent key,
number, form and scope. Editorial notes and secondary catalogue IDs are excluded
from imported names. For example, the source incorrectly associates Chopin's
Rondo Op. 1 with `이별의 왈츠`; that note is not imported. A note mentioning
BWV 924 inside a BWV 924a entry cannot identify BWV 924. Track labels do not rename
an unrelated work header, and collection names do not rename individual members.

### Verified production result

- 814 missing Korean titles filled, increasing coverage from 2,390 to 3,204 of
  11,646 works. **8,442 works still have no Korean display title.**
- 2,567 aliases added: 1,784 Korean and 783 English. Total aliases: 39,090.
- All previous titles, aliases, composer rows, 229 program items, crosswalks and
  non-title work fields preserved. All 11,642 imported review-only works remain so.
- All 977 provenance records verified against the immutable manifest digest.
  Replaying the manifest proposes zero title or alias changes.
- 48 searches checked against the full production catalog, including all 38
  earlier cases. A separate check confirms the incorrect Rondo nickname is absent.

The full-catalog probe exposed two retrieval issues. Bare numeric tokens now
match whole numbers (`Op. 1` does not fully match `Op. 12`), and an explicitly
requested catalogue subnumber receives a small ranking preference over its
collection when old aliases overlap. Both changes were preceded by failing tests.
Search still supports partial-match fallback; a low-ranked result is not evidence
that the query is an accepted identity alias. Existing source-imported collection
aliases remain untouched and still need separate identity review.

The public evidence file now contains seven datasets and preserves all six prior
datasets. It exposes factual names and source references, not database UUIDs,
previous-title guards, editorial prose, artwork or audio. Verification and release
checks are recorded with the change. Local verification passes 378 Python tests,
15 shared tests, 76 web tests, scoped Ruff, ESLint and the Next.js production
build. Review was sequential in this task, not independent-agent review.
This batch does not establish complete
Korean coverage, measured popularity, or 100% automatic work-matching accuracy.

## Complete remaining-target audit (2026-10-21)

All 8,442 works without a Korean display title at the start of this pass now have
an explicit research outcome. This completes the bounded source audit, not Korean
translation of every work or an exhaustive search of the web.

- 430 works received observed Korean titles.
- 141 were held for identity, scope, instrument, or source-text conflicts.
- 7,803 had no compatible Korean title in the checked sources.
- 68 had unavailable linked catalogue sources and no accepted Korean title.

The pass refreshed every target's Wikidata entity and checked 2,718 linked
English Wikipedia article requests (2,716 identity-valid articles). It checked
114 composer identities on public Korean/US Apple Music Classical artist pages
(228 responses, including eight 404s) and 287 selected albums in both locales
(574 responses, including eight 404s). These supplied 1,413 artist-page and 1,783
album-page bilingual observations. The earlier 47-album corpus and 204 Korean
composer/work-list documents were also compared. Album selection followed public
links containing complete, edition, collected, integral, all the, works, sonatas,
symphonies, or concertos; it did not enumerate Apple's entire catalogue.

Exactly one remaining entity supplied an explicit Apple Classical work ID; its
two locale pages were checked. The 3,524 MusicBrainz-linked entities were not
queried through that API because commercial API access was not configured. Their
audit entries state this limitation. No audio, artwork, private endpoint or
search endpoint was collected. Names observed in a publisher catalogue do not
establish which name is most popular among Korean listeners.

The catalogue-less fallback requires a unique full title or existing alias within
the same composer, consistent Korean/English catalogue information, and no known
key, number or scope conflict. It does not use fuzzy matching or an LLM. Imported
names do not promote a work out of review-only status. Twelve manually held
identities are listed in `workers/data/work-name-audit-review.json`.

Three independent public sources resolved four publisher-name issues:

- [Seoul Arts Center programme](https://www.sac.or.kr/site/main/show/show_view?SN=49084)
  supports Vivaldi's Gloria and Handel's Dixit Dominus names.
- [Inmun360 music article](https://inmun360.culture.go.kr/content/357.do?cid=102728&mode=view&page=)
  supports Cage's Music of Changes; the publisher's unrelated Korean name is excluded.
- [Catholic newspaper music column](https://news.catholic.or.kr/WZ_NP/section/view.asp?cseq=3&seq=216753&tbcode=SEC08)
  supports Respighi's Vetrate di chiesa; the publisher's misspelling is excluded.

### Application and verification

`workers/data/korean-full-audit-names.json` is immutable version
`2026-10-21.full-audit.names.1`, digest
`8d048cb7de05d0247ed2c549b55b391356d3362126201fd22045e1bfd0dbc05c`.
The existing guarded importer filled 430 previously null titles and added 590
aliases (434 Korean, 156 English). Production now has 3,634 Korean titles among
11,646 works, 8,012 missing titles, and 39,680 aliases.

Readback confirmed all previous titles/aliases, 209 composers, 229 program items,
canonical crosswalks and non-title work fields were preserved. All 11,642 imported
review-only works remain review-only. All 430 naming provenance records match the
manifest. Replaying it proposes zero title or alias changes.

`/reference/work-name-audit.json` records all 8,442 outcomes with source URLs,
available revisions, observation times/hashes, conflicts and limitations. Digest:
`2c193ef30e89eb1f05f17febc5e9085f4e48270484cd7c8c78004bbeb4d96443`.
All 8,442 corresponding `provider_records` with entity type `work_name_audit`
were read back and compared with the planned payloads. The audit is an on-demand
reference download, not a homepage data dependency. The existing public naming
reference has eight datasets; its prior seven datasets are unchanged.

Local checks pass 402 Python tests, 15 shared tests, 76 web tests, scoped Ruff,
ESLint and the production build. Tests cover incomplete/incorrect source IDs,
composer/name ambiguity, catalogue/key/scope conflicts, public work/composer
pairing, exact target coverage, evidence integrity and canonical identity guards.

Search verification against a fresh production readback passed 1,068 queries:
48 previous regression cases, all 430 new display names and all 590 new aliases.
The previous cases retained their expected first match. New queries combined the
composer, observed name and existing catalogue number; each expected work was
returned, with a worst rank of six. This is not a claim that every bare alias is
unique or always ranks first.

Review ran sequentially in the main task, per the user's execution constraint;
it was not independent-agent review. Code review: skipped (ce-code-review
unavailable). The dedicated multi-agent flow could not produce an independent
receipt under that constraint. Manual validation covered the full new Python
module, tests, manifest identities and source evidence, data-preservation guards,
partial-run recovery, and the generated audit. No blocking issue remained.

### Reapplication and recovery

Use the existing importer with `--dictionary workers/data/korean-full-audit-names.json`
and a local `--report` path. Omit `--apply` first. It checks the exact Classic
Hubble project, composer, canonical title and previous Korean title. Names and
provenance are additive; a partial run can resume without replacing old aliases.

For audit records, `catalog_name_audit.plan_audit` validates the fingerprint and
current canonical crosswalk before the existing `apply_plan` writes provenance
in conflict-ignored batches. Do not edit an applied artifact; create a new version
for corrections. Keep original audit history.

Rollback requires the saved application report, not a blanket deletion: restore
only titles whose current value still equals this batch's imported value, and
remove only newly inserted aliases with this manifest's source digest and exact
work/name identity. Preserve later edits, prior aliases and all provenance. No
schema, authentication, collection schedule or automatic programme matching rule
changed in this pass.
