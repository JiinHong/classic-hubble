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
or more direct source URLs, and a review status. The focused data test enforces
that the provenance keys and display names stay in lockstep with the runtime
dictionary, that every entry has source evidence, and that entries marked
`reviewed` have at least two direct source links.

Korean labels were seeded from Korean Wikipedia/Wikidata labels and Korean
Wikipedia page titles, then reviewed against independent identity evidence and
Korean-facing usage where available. Evidence recorded in the provenance file
uses stable direct links, including Wikidata composer entities, Korean
Wikipedia articles, MusicBrainz artist pages, and English Wikipedia identity
articles for alternate Open Opus spellings or sparse Korean coverage.
Examples used to resolve common-form differences include:

- Korean Wikipedia/Wikidata baseline pages such as
  `https://ko.wikipedia.org/wiki/에런_코플런드`,
  `https://ko.wikipedia.org/wiki/버르토크_벨러`, and Wikidata labels queried
  through `https://query.wikidata.org/sparql`.
- Concert and venue sources such as Seoul Arts Center
  `https://www.sac.or.kr/`, Lotte Concert Hall
  `https://www.lotteconcerthall.com/`, and Sejong Center
  `https://www.sejongpac.or.kr/`.
- Catalog/streaming references such as Yes24
  `https://www.yes24.com/`, Apple Music Classical
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

When Korean institutional or catalog usage is sparse, the provenance entry uses
`review.status: "sparse-ko-institutional-usage"` and must include a note. Those
entries retain conservative Hangul transliterations while documenting direct
identity evidence instead of pretending that a Korean institutional consensus
exists. Examples currently marked sparse include `Camargo Guarnieri`,
`Joly Braga Santos`, and `Vagn Holmboe`.

## Open Opus Composer Portraits

- Source: https://www.openopus.org/
- Portrait API: `https://api.openopus.org/composer/list/name/{initial}.json`
- Asset host: `https://assets.openopus.org/portraits/`
- Snapshot date: 2026-07-29
- License: public domain, as stated at https://www.openopus.org/
- Retained fields: portrait image only
- Local destination: `apps/web/public/composer-portraits/`
- File count: 29 curated period representatives and fallbacks

Portraits are committed as local 200-by-200 JPEG files. The application does
not call Open Opus or its asset host at runtime, and no birth or death fields
are retained.
