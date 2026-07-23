# Composer Directory Design

## Summary

Classic Hubble will add one focused composer directory at `/composers`. Its purpose is to let a visitor scan, search, and filter every composer in the catalog without navigating through cards, portraits, rankings, or editorial content.

## Goals

- Show all cataloged composers on one page.
- Make Korean-name scanning the default behavior.
- Let users narrow the list by musical period.
- Let users search Korean and original-language names.
- Mark core composers without hiding or visually diminishing other composers.
- Connect a composer name to the existing work and performance discovery flow.

## Non-Goals

- Composer biographies, portraits, timelines, and birth/death years.
- Popularity rankings or personalized recommendations.
- A separate composer detail page in this iteration.
- Claims that the initial catalog contains every composer who has ever existed.

## Page Structure

### Header

Add `작곡가` to the primary application navigation. The page itself starts directly with the directory controls and does not use a marketing hero.

### Controls

The controls appear in this order:

1. A search field with the placeholder `작곡가 이름 검색`.
2. A segmented period filter: `전체`, `중세`, `르네상스`, `바로크`, `고전`, `낭만`, `20세기`, `현대`.
3. A two-option sort control: `가나다순` and `A–Z`.
4. A result count that updates after filtering.

Search and filtering run locally after the server has loaded the composer directory. Search is case-insensitive and matches both `name_ko` and `name`.

### Composer List

Composers are grouped under visible period headings. Within each period:

- Desktop uses four text columns.
- Tablet uses two text columns.
- Mobile uses one text column.
- Each row shows the Korean name as the primary label.
- The original-language name appears below in smaller muted text.
- No dates, image containers, or decorative cards are shown.

Core composers use a heavier primary name and a small `핵심` label. Their row dimensions and position remain the same as every other composer. Non-core composers are never collapsed behind a secondary action.

### Composer Selection

Selecting a composer links to `/?composer=<encoded-primary-name>`, using the Korean name when available and the original name otherwise. The existing discovery page reads that query parameter, opens with the composer selected, and shows matching works and upcoming performances. This avoids adding a second composer-specific page or a database field that only exists for routing.

### Empty and Error States

- A filter with no matches shows `조건에 맞는 작곡가가 없습니다`.
- If Supabase cannot be reached, the existing local catalog fallback is used.
- If both sources fail, the page shows a compact retry state instead of an empty directory.

## Data Model

The composer directory uses the existing `composers` table fields:

- `id`
- `name`
- `name_ko`
- `period`

Period values are normalized to seven named periods during catalog ingestion. The UI includes an eighth `기타` group when it receives an unknown period so records are not lost.

The repository includes a composer-only snapshot from the public-domain Open Opus dataset as the baseline catalog. Birth/death dates, portraits, and works are not copied into this snapshot. The page does not call Open Opus at runtime.

The catalog loader merges every Supabase composer row into the baseline by normalized original-language name. Supabase values take precedence, so curated Korean names and period corrections appear immediately. When no Korean name exists, the original name is used once as the primary label rather than duplicated.

The page renders the complete merged catalog. A small reviewed `CORE_COMPOSER_NAMES` set in the directory module derives the core marker without changing the database schema. Open Opus is a practical baseline rather than a claim to include every composer who has ever existed, and the directory must not impose an arbitrary display limit.

## Component Boundaries

- `ComposerDirectoryPage`: server component that loads composer data.
- `ComposerDirectory`: client component that owns search, filtering, sorting, and result count.
- `ComposerPeriodFilter`: segmented period control.
- `ComposerList`: period grouping and responsive columns.
- `ComposerListItem`: composer link and core marker.
- `composer-directory.ts`: pure normalization, search, grouping, and sorting functions.

Pure directory functions remain independent from React so they can be tested without rendering the page.

## Accessibility

- Search has a visible label.
- Period and sort controls expose their selected state.
- Composer entries are normal keyboard-focusable links.
- Core status is available as text, not color alone.
- Focus styles remain visible.
- The list keeps document order consistent with visual order at every breakpoint.

## Testing Strategy

Implementation follows TDD:

1. Write failing unit tests for period normalization, Korean/original-name search, and both sort modes.
2. Write failing component tests for filter selection, result count, no-results state, and core marking.
3. Write failing navigation tests for the composer query link.
4. Implement the smallest code needed to pass each test.
5. Run the web test suite, lint, and production build.
6. Verify desktop and mobile layouts in the browser.

## Acceptance Criteria

- `/composers` is accessible from the primary navigation.
- All loaded composers are visible by default.
- Search matches Korean and original-language names.
- Period filters and sort controls work without navigation or reload.
- Composer rows display no birth/death years.
- Core composers are recognizable but occupy the same layout as other entries.
- Selecting a composer opens filtered works and performances.
- The page remains readable at desktop and mobile widths.
- Tests, lint, and production build pass.
