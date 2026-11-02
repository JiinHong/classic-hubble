# Targeted Performance Search and YouTube Identification

**Goal:** Remove full-catalog downloads from performance search and YouTube identification without changing the existing TypeScript decisions or public results.

**Approved design:** Add invoker-rights Supabase candidate functions and useful indexes. Keep original work/performance data and final matching rules unchanged. Do not fall back to full-catalog downloads on errors.

**Architecture:** Reuse work-search candidate retrieval, including component-family expansion. Performance candidates are upcoming, city-filtered, and match either public text or matched work IDs; TypeScript still filters, sorts, and paginates. YouTube retrieval deliberately over-selects mentioned composers and contained titles/aliases, then expands component families. A lossy ASCII/Hangul decomposition key is only a recall filter, never a match decision; names with an empty key are retained. This avoids requiring SQL to reproduce JavaScript Unicode matching. Fetch upcoming performance links only for final selected works, in the old chronological order.

**Implementation sequence:**
1. Characterize old outputs and capture one reusable raw snapshot, with measured DB response bodies. Add failing route/retrieval tests.
2. Extract shared work candidate/family loading; add targeted performance and YouTube services. Keep pure matchers unchanged.
3. Add the SQL migration, test candidate recall, pagination, permissions, literal text, nulls, components, and error propagation. Apply only to project klnfamtwxwrelrjeguqb.
4. Compare old/new outputs using frozen time and inputs, including ambiguity and upcoming IDs. Reuse the local baseline snapshot instead of downloading it repeatedly.
5. Run tests, lint, build, review, and browser/API verification. Record timing and decoded DB response bytes separately from client response bytes and actual billed egress. Ship through the existing PR workflow.

**Baseline:** Production GET /api/catalog/search?q=베토벤&mode=performances&city=전체&offset=0 at 2026-11-02T01:40:35Z: catalog 11830.3 ms, search 1187.0 ms, HTTP total 14143.1 ms, client response 15543 bytes. This client size is not DB transfer. Initial focused tests: 46 passing across five files.

**Verification:** Route tests must reject the old full-catalog path. Read-only integration and local snapshot parity compare complete outputs across empty, city, title, alias, shorthand, catalogue, unknown, component, credit, timestamp, and ambiguous inputs. All candidate pages must be read; no arbitrary top-N pruning.

**Out of scope:** OCR, billing-plan changes, matcher policy changes, public source-data changes, unrelated dirty files.
