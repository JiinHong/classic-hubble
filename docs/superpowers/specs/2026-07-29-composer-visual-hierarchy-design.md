# Composer Visual Hierarchy Design

## Summary

The composer directory will stop labeling individual people as `핵심`. Instead,
each musical period will begin with up to four portrait-led composer links. The
complete, evenly styled composer list remains directly below so every catalog
entry is still easy to scan.

This design was approved in the conversation on 2026-07-29.

## Visual Structure

- Keep the existing page title, count, search, period filter, and sort controls.
- Keep period sections in musical chronology.
- Place up to four curated portrait links immediately below each period heading.
- Use position, portrait, spacing, and slightly stronger type as the only
  importance signals.
- Do not render `핵심`, stars, ranks, status pills, or popularity numbers.
- Render the complete composer list below the portrait links, including the
  composers already shown above.
- Use four portrait columns on desktop and two on mobile.
- Use four full-list columns on desktop and two on mobile.

## Behavior

- Featured portrait order is editorial and does not change with 가나다/A-Z sort.
- Full-list ordering continues to follow the selected sort.
- Selecting either representation opens the existing composer discovery link.
- Hide portrait links while a name search is active to avoid duplicate
  single-result presentation.
- A selected period shows only that period and its portrait links.
- Periods without curated portraits fall back to the complete list.

## Data

- Keep editorial metadata in the pure composer directory module.
- Store `featuredRank` and a local `portraitSrc` on normalized directory entries.
- Select no more than four portrait entries from any one period.
- Use locally committed Open Opus portrait assets so production rendering does
  not depend on the portrait host at request time.
- Preserve the existing Korean labels and add Korean labels for newly featured
  composers.

## Accessibility

- Portraits are decorative because the adjacent composer name is the link label.
- Featured and complete lists remain semantic lists.
- The featured list receives a period-specific accessible label.
- Keyboard focus styles remain visible.
- Visual importance is not communicated by color alone.

## Testing

- Pure tests cover featured metadata, stable editorial ordering, and the
  four-person limit.
- Component tests prove that no `핵심` text is rendered, portrait links appear
  before the complete list, featured composers remain in the complete list, and
  search hides duplicate portrait links.
- Run all tests, lint, and the production build.
- Verify desktop and mobile layouts with browser screenshots.
