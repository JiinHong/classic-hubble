# Reviewed Korean Work Names

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
