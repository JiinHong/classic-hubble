# Composer Korean Names And Deduplication Design

## Summary

The composer directory will show each composer only once during normal
browsing. A composer represented by a portrait card will not be repeated in
the plain list below it. While search is active, portrait cards remain hidden
and all matching composers, including portrait composers, appear in the plain
search results.

Every composer in the current 220-person Open Opus baseline will receive a
reviewed Korean display name. Plain composer links will show the Korean name
first and the original English or Latin-script name below it.

This design was approved in the conversation on 2026-07-31.

## Korean Name Policy

- Keep a static, version-controlled dictionary keyed by normalized original
  composer name.
- Cover every composer in the current Open Opus baseline.
- Prefer the Korean form used repeatedly across independent Korean-language
  sources.
- Use Korean Wikipedia and Wikidata as the initial candidate source, then
  resolve uncertain or competing forms with Google search evidence from
  sources such as KOPIS, major Korean concert halls, music catalogs, press,
  and established community references.
- Do not select a form solely because one community page or one search result
  uses it.
- Prefer recognizability in Korean classical-music usage over rigid mechanical
  transliteration when a conventional name is established.
- Preserve an explicit `name_ko` supplied by Supabase. The fixed dictionary is
  the fallback for baseline rows whose Korean name is empty.
- Do not invent an automatic Korean transliteration for future composers that
  have not been reviewed.
- Record the source categories, review date, and snapshot scope in the project
  data-source documentation. Runtime rendering must not depend on search,
  Wikidata, or another external naming service.

## Data Design

- Add `apps/web/src/data/composer-korean-names.json` as the fixed display-name
  dictionary.
- Keep `openopus-composers.json` as the retained source snapshot rather than
  mixing project-owned localization into the upstream data.
- Build the dictionary lookup once in `composer-directory.ts` and use it from
  `toComposerDirectoryEntry`.
- Require the dictionary keys to match the 220 baseline composer names exactly.
  Tests fail for missing entries, stale extra entries, empty labels, or labels
  without Hangul.

## Rendering Behavior

- Keep period headings, portrait-card order, sort controls, filters, and total
  unique-composer counts unchanged.
- During normal browsing, select up to four portrait composers for each period
  and remove those exact identities from the plain list in that period.
- Do not render an empty plain list when every visible composer in a period is
  already represented by portrait cards.
- Use a neutral accessible label such as `바로크 작곡가 목록` for the plain
  list because it may contain either all search results or only non-featured
  browsing results.
- While a query is non-empty, do not render portrait cards and do not remove
  any matching composer from the plain results.
- Plain list items render the reviewed Korean name as the primary line and the
  original name as the secondary line.
- A future composer without a reviewed Korean label may retain its original
  name as the only line until the dictionary is updated.

## Site Footer

- Add one shared footer to the root application layout so it appears at the
  bottom of every page.
- Separate the footer from page content with a thin neutral border.
- Render `Classic Hubble by Jimin, Jinhong` as the primary line.
- Render `© 2026 Classic Hubble. All rights reserved.` as the secondary line.
- Keep both lines readable but visually subordinate to page content.
- Match the existing light stone and emerald visual system rather than copying
  the dark colors from the reference screenshot.
- Do not add social links, language controls, legal links, or additional
  branding in this change.

## Testing

- Snapshot tests prove exact dictionary coverage of all 220 baseline names and
  validate that every reviewed label contains Hangul.
- Pure tests prove that explicit Supabase Korean names override the dictionary
  and that dictionary names fill empty database values.
- Component tests prove that featured composers appear once in normal browsing,
  return once in search results, and do not change the displayed total count.
- Component tests prove Korean-before-original DOM order for plain list items
  and verify that an empty remainder list is omitted.
- A layout test proves that the shared footer renders the approved maker and
  copyright text.
- Run the complete test suite, lint, and production build.
- Verify the production page at desktop and mobile widths, including search,
  period filtering, footer placement, text overflow, duplicate links, and
  browser console errors.
