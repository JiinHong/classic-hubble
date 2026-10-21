# Korean Catalog Naming Continuation

Continue source-observed Korean title and alias enrichment for the 9,455 works
still missing a Korean title after PR #11. Preserve existing display titles,
canonical identities, prior aliases, concert associations and review-only flags.
Do not invent audience shorthand, translate unknown programmatic titles or
represent a source-observed name as a measured popularity ranking.

## Approach

1. Snapshot live catalog rows; enumerate all represented composers and inspect
   their Korean reference pages and linked work lists, reusing cached responses.
2. Extend only the source extraction patterns that appear in those pages, with
   failing tests before implementation. Use complete composer/catalogue identity,
   exclude ambiguous arrangements/collections, retain evidence and rejection reasons.
3. Review candidate names, import the additive manifest with the existing guarded
   importer, read back every change and verify repeat application is a no-op.
4. Publish source attribution and coverage counts, verify Korean searches, run
   tests/build, and release through the existing GitHub/Vercel workflow.

## Verification

The full remaining catalog is the research scope, not a promise that every obscure
work has an established Korean name. Report verified additions and unresolved
coverage separately. Every title must have an observed Korean source and a
specific identity anchor; conflicts must not be resolved merely to increase totals.
Data changes receive complete before/after comparison and sampled search checks.
Code changes receive focused red/green tests and the full worker suite.

The current task executes sequentially under the user's AGENTS instructions;
review is same-thread, not an independent-agent review. Untracked capstone
documents are excluded from commits. Release evidence is recorded on the PR.
