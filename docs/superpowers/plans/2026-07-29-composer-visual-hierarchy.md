# Composer Visual Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace visible `핵심` badges with portrait-led, period-specific visual hierarchy while preserving the complete composer directory.

**Architecture:** Pure composer metadata derives Korean labels, featured rank,
and local portrait paths. `ComposerList` renders a small featured list before the
existing complete list, while `ComposerDirectory` suppresses the featured list
during active search.

**Tech Stack:** Next.js 16, React 19, TypeScript 5, Tailwind CSS 4, Vitest 4,
React Testing Library, local JPEG assets.

## Global Constraints

- No visible `핵심`, star, rank, pill, or popularity label.
- At most four featured composers per period.
- Featured order does not change with directory sort.
- Every composer remains in the complete list.
- Search, period filtering, and discovery links keep their current behavior.
- Implementation follows failing test, observed failure, minimal code, and
  passing test.

---

### Task 1: Featured Composer Rules

**Files:**
- Modify: `apps/web/src/lib/composer-directory.test.ts`
- Modify: `apps/web/src/lib/composer-directory.ts`

**Interfaces:**
- Produces: `featuredRank: number | null`, `portraitSrc: string | null`
- Produces: `selectFeaturedComposers(entries): ComposerDirectoryEntry[]`

- [ ] Add tests asserting that curated entries have Korean labels and portraits.
- [ ] Add a test that selection is editorially ordered and capped at four.
- [ ] Run the focused unit test and observe the missing-interface failure.
- [ ] Add the minimum metadata and selector implementation.
- [ ] Re-run the focused unit test and confirm it passes.

### Task 2: Badge-Free Featured Presentation

**Files:**
- Create: `apps/web/src/components/FeaturedComposerCard.tsx`
- Modify: `apps/web/src/components/ComposerDirectory.test.tsx`
- Modify: `apps/web/src/components/ComposerDirectory.tsx`
- Modify: `apps/web/src/components/ComposerList.tsx`
- Modify: `apps/web/src/components/ComposerListItem.tsx`

**Interfaces:**
- `ComposerList` consumes `showFeatured: boolean`.
- `FeaturedComposerCard` consumes one normalized directory entry.

- [ ] Replace the core-badge assertion with failing hierarchy assertions.
- [ ] Run the focused component test and observe the expected failure.
- [ ] Add portrait cards, remove badge markup, and pass search visibility state.
- [ ] Re-run the focused component test and confirm it passes.

### Task 3: Local Portrait Assets

**Files:**
- Create: `apps/web/public/composer-portraits/*.jpg`
- Modify: `docs/data-sources.md`

- [ ] Download only the curated Open Opus portrait files.
- [ ] Verify every configured local path exists and decodes as an image.
- [ ] Record the retained portrait source and snapshot date.

### Task 4: Verification And Release

**Files:**
- No new interfaces.

- [ ] Run `pnpm test`.
- [ ] Run `pnpm lint`.
- [ ] Run `pnpm build`.
- [ ] Inspect desktop and mobile screenshots and fix overflow or hierarchy issues.
- [ ] Commit, merge to `main`, push, and verify the production Vercel deployment.
