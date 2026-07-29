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
