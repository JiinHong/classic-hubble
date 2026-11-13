# Data Sources

## Open Opus Composer Baseline

- Source: https://www.openopus.org/
- Snapshot endpoint: https://api.openopus.org/work/dump.json
- Snapshot date: 2026-07-23
- License: public domain, as stated at https://www.openopus.org/
- Retained fields: `complete_name` as `name`, `epoch` as `period`
- Excluded fields: birth, death, portrait, popularity flags, and works

The snapshot is committed so `/composers` does not depend on Open Opus at runtime.
Supabase rows override matching names and provide curated Korean labels where available.

## Reviewed Korean Composer Names

- Local file: `apps/web/src/data/composer-korean-names.json`
- Provenance file: `apps/web/src/data/composer-korean-name-provenance.json`
- Review date: 2026-07-31
- Scope: all 220 composer names in `apps/web/src/data/openopus-composers.json`
- Runtime behavior: static local lookup only; no Wikidata, Wikipedia, search, or
  catalog service calls at runtime
- Precedence: explicit Supabase `name_ko` values remain authoritative over the
  fixed dictionary

`composer-korean-name-provenance.json` is the version-controlled review record
for the display dictionary. Its top-level keys must exactly match
`composer-korean-names.json`; each entry records the chosen `displayName`, one
or more direct source URLs, and a review status. Every display label in the
dictionary was manually reviewed, but the review status reports the strength of
the recorded Korean-usage corroboration rather than whether a human looked at
the label. The focused data test enforces that the provenance keys and display
names stay in lockstep with the runtime dictionary, that every entry has source
evidence, and that entries marked `reviewed` have at least two direct
Korean-facing, composer-specific source URLs from distinct publishers whose
recorded source titles explicitly contain the selected `displayName`. Generic
homepages, search URLs, alternate-spelling pages, Wikidata labels, MusicBrainz
pages, and non-Korean identity links do not count toward that `reviewed`
threshold.

Korean labels were seeded from Korean Wikipedia/Wikidata labels and Korean
Wikipedia page titles, then manually reviewed against independent identity
evidence and Korean-facing usage where available. Evidence recorded in the
provenance file uses stable direct links, including Wikidata composer entities,
Korean Wikipedia articles, MusicBrainz artist pages, and English Wikipedia
identity articles for alternate Open Opus spellings or sparse Korean coverage.
Only direct Korean-facing pages that identify or support the intended composer
and record the exact selected display form count as corroboration for
`reviewed`. Examples used to resolve common-form differences include:

- Korean Wikipedia/Wikidata baseline pages such as
  `https://ko.wikipedia.org/wiki/에런_코플런드`,
  `https://ko.wikipedia.org/wiki/버르토크_벨러`, and Wikidata labels queried
  through `https://query.wikidata.org/sparql`.
- Direct concert and venue pages such as Seoul Philharmonic
  `https://www.seoulphil.or.kr/perf/view?langCd=ko&menuFlag=MFLG0001&perfNo=5304`
  and Daejeon Arts Center
  `https://www.daejeon.go.kr/djac/performanceView.do?code=2818&menuSeq=6709&type=image&yyyymm=202305`.
- Catalog/streaming references such as Yes24
  `https://www.yes24.com/product/goods/29786887`, Apple Music Classical
  `https://music.apple.com/`, medici.tv Korea `https://www.medici.tv/ko/`,
  and Berlin Philharmonic Digital Concert Hall
  `https://www.digitalconcerthall.com/ko/`.
- Korean press and community/classical music references, used only as
  corroborating evidence when institutional and catalog sources disagreed or
  were sparse.

Where Korean Wikipedia used a formal native-order title but Korean concert and
catalog sources repeatedly used a more recognizable concert form, the dictionary
uses the repeated concert form; for example `Béla Bartók` is stored as
`벨라 바르톡`. Where the database seed already contains a Korean label, that
explicit Supabase label remains the authoritative display value for matching
Supabase rows.

When the recorded evidence lacks two qualifying Korean-facing direct sources
from distinct publishers using the exact selected display form, the provenance
entry uses
`review.status: "sparse-ko-institutional-usage"` and must include a note. Those
entries retain manually reviewed conservative Hangul labels while documenting
identity evidence instead of pretending that a Korean institutional consensus is
already recorded. Examples currently marked sparse include `Aaron Copland`,
`Camargo Guarnieri`, `Joly Braga Santos`, `Vagn Holmboe`, `Arnold Bax`, and
`Wilhelm Stenhammar`.

Alternate spellings may remain in provenance as identity context without
counting toward `reviewed`; for example Daejeon Arts Center identifies
`Josef Suk (1874-1935)` under `요제프 수크`, while the selected display form
`요세프 수크` is corroborated by Seoul Philharmonic and Yes24.

## Open Opus Composer Portraits

- Source: https://www.openopus.org/
- Portrait API: `https://api.openopus.org/composer/list/name/{initial}.json`
- Asset host: `https://assets.openopus.org/portraits/`
- Snapshot date: 2026-07-29
- License: public domain, as stated at https://www.openopus.org/
- Retained fields: portrait image only
- Local destination: `apps/web/public/composer-portraits/`
- File count: 29 curated period representatives and fallbacks

The original 29 JPEGs are unchanged. Composer search and profiles also use 191
local 200px WebP portraits generated from the remaining named files in
[Open Opus's official portrait collection](https://github.com/openopus-org/openopus_api/tree/fc713e1bdb1e5704ae93e6f3f60ee5e028cb8a73/portraits).
Files are matched against the reviewed full-name baseline; shared surnames
have explicit mappings. No remote portrait provider is called during search.

## Composer profiles and suggestions (2026-11-13)

- The small, checked-in name index contains only public IDs, names and periods
  from Classic Hubble and the Open Opus baseline. After composer imports, run
  `node --env-file=<public-web-env> apps/web/scripts/refresh-composer-index.mjs`
  and deploy the refreshed snapshot. Work lists are not in the index: profile
  pages read the current composer's works by ID, 24 at a time.
- 130 short Korean descriptions are sourced from Wikidata (CC0) using the
  individually reviewed entity IDs in the Korean-name provenance. The four
  longer editorial notes link to their institutional sources on each profile.
  Where no description exists we use catalog facts, not generated biographies.
- To refresh media, extract the pinned Open Opus source and run
  `node apps/web/scripts/refresh-composer-media.mjs /path/to/openopus/portraits`.
  Source identities and Korean descriptions are resolved at refresh time only.
