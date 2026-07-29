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
