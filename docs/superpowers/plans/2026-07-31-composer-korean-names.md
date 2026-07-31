# Composer Korean Names And Footer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove portrait-card duplicates from normal composer browsing, give all 220 baseline composers reviewed Korean display names, and add the approved shared site footer.

**Architecture:** A project-owned JSON dictionary provides deterministic Korean names without a runtime network dependency, while explicit Supabase localization remains authoritative. `ComposerList` derives a non-featured remainder only during normal browsing, and a small shared `SiteFooter` is mounted by the root layout.

**Tech Stack:** Next.js 16, React 19, TypeScript 5, Tailwind CSS 4, Vitest 4, React Testing Library, static JSON data.

## Global Constraints

- Display `Classic Hubble by Jimin & Jinhong`.
- Display `© 2026 Classic Hubble. All rights reserved.`.
- Cover all 220 composers in the current Open Opus snapshot with reviewed Korean names.
- Prefer repeated Korean-language usage across independent sources over mechanical transliteration.
- Preserve explicit Supabase `name_ko` values.
- Do not use a runtime naming API.
- Hide portrait composers from the plain list during normal browsing.
- Restore portrait composers to the plain results while search is active.
- Keep displayed composer totals based on unique composers, not rendered links.
- Use failing-test, observed-failure, minimal-fix, passing-test cycles.

---

### Task 1: Reviewed Korean Composer Dictionary

**Files:**
- Create: `apps/web/src/data/composer-korean-names.json`
- Modify: `apps/web/src/data/openopus-composers.test.ts`
- Modify: `apps/web/src/lib/composer-directory.ts`
- Modify: `apps/web/src/lib/composer-directory.test.ts`
- Modify: `docs/data-sources.md`

**Interfaces:**
- Produces: `composer-korean-names.json`, an object whose original-name keys exactly match the Open Opus baseline and whose values are reviewed Korean labels.
- Produces: `koreanComposerLabel(identityKey: string): string | undefined`.
- Preserves: `toComposerDirectoryEntry(input).nameKo` precedence of explicit input, fixed dictionary, then original name.

- [ ] **Step 1: Add failing dictionary coverage assertions**

Replace the old `nameKo === null` assertion in
`openopus-composers.test.ts` with an import and exact-coverage checks:

```ts
import koreanNames from "./composer-korean-names.json";

const originalNames = composers.map((composer) => composer.name).toSorted();
const localizedNames = Object.keys(koreanNames).toSorted();

expect(localizedNames).toEqual(originalNames);
expect(Object.values(koreanNames)).toHaveLength(composers.length);

for (const label of Object.values(koreanNames)) {
  expect(label.trim()).toBe(label);
  expect(label).toMatch(/[가-힣]/);
}
```

- [ ] **Step 2: Run the snapshot test and observe the missing-module failure**

Run:

```bash
pnpm --filter web test -- src/data/openopus-composers.test.ts
```

Expected: FAIL because `composer-korean-names.json` does not exist.

- [ ] **Step 3: Research and create the complete fixed dictionary**

Create one JSON object with all 220 original names as keys. Seed candidates
from Korean Wikipedia/Wikidata labels, then use Google search to resolve
uncertain forms by comparing independent Korean sources such as KOPIS, major
concert halls, established music catalogs or press, and community references.
Use the form repeated across sources and document the review date and source
categories in `docs/data-sources.md`.

The file shape is:

```json
{
  "Aaron Copland": "에런 코플런드",
  "Alban Berg": "알반 베르크",
  "Albert Roussel": "알베르 루셀"
}
```

The completed file must satisfy this exact structural check:

```bash
jq --argfile source apps/web/src/data/openopus-composers.json \
  'keys | length == ($source | length)' \
  apps/web/src/data/composer-korean-names.json
```

Expected: `true`.

- [ ] **Step 4: Add failing normalization precedence tests**

Add these cases to `composer-directory.test.ts`:

```ts
it("uses the reviewed Korean dictionary when the source label is empty", () => {
  expect(
    toComposerDirectoryEntry({
      id: "copland",
      name: "Aaron Copland",
      nameKo: null,
      period: "20th Century",
    }).nameKo,
  ).toBe("에런 코플런드");
});

it("keeps an explicit source label ahead of the reviewed dictionary", () => {
  expect(
    toComposerDirectoryEntry({
      id: "copland",
      name: "Aaron Copland",
      nameKo: "애런 코플랜드",
      period: "20th Century",
    }).nameKo,
  ).toBe("애런 코플랜드");
});
```

- [ ] **Step 5: Run the focused rule test and observe the fallback failure**

Run:

```bash
pnpm --filter web test -- src/lib/composer-directory.test.ts
```

Expected: FAIL because `Aaron Copland` is not yet read from the new dictionary.

- [ ] **Step 6: Replace partial in-module labels with the fixed dictionary**

Import the JSON, build one normalized map, and keep explicit input precedence:

```ts
import koreanComposerNames from "@/data/composer-korean-names.json";

const KOREAN_COMPOSER_LABELS = new Map(
  Object.entries(koreanComposerNames).map(([name, nameKo]) => [
    normalizeText(name),
    nameKo,
  ]),
);

function koreanComposerLabel(identityKey: string) {
  return KOREAN_COMPOSER_LABELS.get(identityKey);
}
```

Keep featured rank and portrait metadata separate from localization metadata.
Keep the existing `toComposerDirectoryEntry` order:

```ts
nameKo:
  input.nameKo?.trim() ||
  koreanComposerLabel(identityKey) ||
  input.name.trim(),
```

- [ ] **Step 7: Run focused data and rule tests**

Run:

```bash
pnpm --filter web test -- src/data/openopus-composers.test.ts src/lib/composer-directory.test.ts
```

Expected: PASS.

- [ ] **Step 8: Commit the reviewed localization**

```bash
git add apps/web/src/data/composer-korean-names.json \
  apps/web/src/data/openopus-composers.test.ts \
  apps/web/src/lib/composer-directory.ts \
  apps/web/src/lib/composer-directory.test.ts \
  docs/data-sources.md
git commit -m "feat(web): localize composer directory names"
```

### Task 2: Non-Duplicated Composer Browsing

**Files:**
- Modify: `apps/web/src/components/ComposerDirectory.test.tsx`
- Modify: `apps/web/src/components/ComposerList.tsx`

**Interfaces:**
- Consumes: `selectFeaturedComposers(entries)`.
- Produces: a per-period `plainComposers` list that excludes featured identities only when `showFeatured` is true.

- [ ] **Step 1: Change the hierarchy test to require one normal-view link per featured composer**

Use one non-featured Baroque fixture and assert that featured identities do not
appear in the plain list:

```ts
const plainList = within(baroqueSection!).getByRole("list", {
  name: "바로크 작곡가 목록",
});

expect(
  within(plainList)
    .getAllByRole("link")
    .map((link) => link.getAttribute("href")),
).toEqual([composerHref("도메니코 스카를라티")]);

expect(
  within(baroqueSection!).getAllByRole("link", {
    name: /요한 제바스티안 바흐/,
  }),
).toHaveLength(1);
```

Add an assertion that the plain link renders Korean before the original:

```ts
const plainLink = within(plainList).getByRole("link", {
  name: /도메니코 스카를라티.*Domenico Scarlatti/,
});
expect(plainLink.children[0]?.textContent).toBe("도메니코 스카를라티");
expect(plainLink.children[1]?.textContent).toBe("Domenico Scarlatti");
```

Add a test proving no empty remainder list is rendered when a period contains
only featured composers.

- [ ] **Step 2: Run the component test and observe duplicate/list-label failures**

Run:

```bash
pnpm --filter web test -- src/components/ComposerDirectory.test.tsx
```

Expected: FAIL because the plain list still contains featured composers and is
labelled `전체 작곡가`.

- [ ] **Step 3: Derive and conditionally render the plain remainder**

Inside each period group:

```ts
const featuredComposers = showFeatured
  ? selectFeaturedComposers(group.composers)
  : [];
const featuredIds = new Set(featuredComposers.map((composer) => composer.id));
const plainComposers = showFeatured
  ? group.composers.filter((composer) => !featuredIds.has(composer.id))
  : group.composers;
```

Render the plain list only when it has entries and use the neutral label:

```tsx
{plainComposers.length ? (
  <ul
    aria-label={`${group.label} 작곡가 목록`}
    className="grid grid-cols-2 gap-x-4 sm:gap-x-6 xl:grid-cols-4"
  >
    {plainComposers.map((composer) => (
      <ComposerListItem composer={composer} key={composer.id} />
    ))}
  </ul>
) : null}
```

- [ ] **Step 4: Verify normal browsing, search restoration, counts, and order**

Run:

```bash
pnpm --filter web test -- src/components/ComposerDirectory.test.tsx
```

Expected: PASS, including the existing search test showing one Bach result and
the header count remaining based on all visible unique composers.

- [ ] **Step 5: Commit composer-list behavior**

```bash
git add apps/web/src/components/ComposerDirectory.test.tsx \
  apps/web/src/components/ComposerList.tsx
git commit -m "feat(web): remove duplicate composer links"
```

### Task 3: Shared Site Footer

**Files:**
- Create: `apps/web/src/components/SiteFooter.tsx`
- Create: `apps/web/src/components/SiteFooter.test.tsx`
- Modify: `apps/web/src/app/layout.tsx`

**Interfaces:**
- Produces: `SiteFooter(): React.ReactElement`.
- Root layout renders one footer after a flexible content wrapper.

- [ ] **Step 1: Write the failing footer component test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SiteFooter } from "./SiteFooter";

describe("SiteFooter", () => {
  it("credits the makers and shows the copyright", () => {
    render(<SiteFooter />);

    expect(
      screen.getByText("Classic Hubble by Jimin & Jinhong"),
    ).toBeTruthy();
    expect(
      screen.getByText("© 2026 Classic Hubble. All rights reserved."),
    ).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run the footer test and observe the missing-module failure**

Run:

```bash
pnpm --filter web test -- src/components/SiteFooter.test.tsx
```

Expected: FAIL because `SiteFooter.tsx` does not exist.

- [ ] **Step 3: Implement the restrained shared footer**

```tsx
export function SiteFooter() {
  return (
    <footer className="border-t border-stone-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <p className="text-sm font-black text-stone-800">
          Classic Hubble by Jimin &amp; Jinhong
        </p>
        <p className="mt-1 text-xs font-semibold text-stone-500">
          © 2026 Classic Hubble. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
```

Mount it at the application root and keep it at the viewport bottom on short
pages:

```tsx
import { SiteFooter } from "@/components/SiteFooter";

<body className="flex min-h-full flex-col bg-stone-50 text-stone-950">
  <AuthProvider>
    <UserLibraryProvider>
      <AppHeader />
      <div className="flex-1">{children}</div>
      <SiteFooter />
    </UserLibraryProvider>
  </AuthProvider>
</body>
```

- [ ] **Step 4: Run the footer test**

Run:

```bash
pnpm --filter web test -- src/components/SiteFooter.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit the footer**

```bash
git add apps/web/src/components/SiteFooter.tsx \
  apps/web/src/components/SiteFooter.test.tsx \
  apps/web/src/app/layout.tsx
git commit -m "feat(web): add shared site footer"
```

### Task 4: Full Verification And Release

**Files:**
- Modify only files required by failures found during verification.

**Interfaces:**
- Produces: a verified production deployment from the final `main` commit.

- [ ] **Step 1: Run the complete automated test suite**

```bash
pnpm test
```

Expected: all shared and web tests pass with zero failures.

- [ ] **Step 2: Run lint**

```bash
pnpm lint
```

Expected: exit code 0 with no ESLint errors.

- [ ] **Step 3: Run the production build**

```bash
pnpm build
```

Expected: exit code 0 with the `/composers` route built successfully.

- [ ] **Step 4: Verify local desktop and mobile behavior**

Start the app on an available port and inspect `/composers` at 1440×900 and
390×844. Confirm:

```text
- portrait composers have exactly one link in normal browsing
- searching a portrait composer returns exactly one plain link
- every plain baseline composer has Korean text above the original name
- no horizontal or card overflow
- footer follows content and reaches the viewport bottom on short pages
- no browser console errors
```

- [ ] **Step 5: Review the final diff against the design**

```bash
git diff main...HEAD --check
git diff main...HEAD --stat
git status --short
```

Expected: no whitespace errors, only scoped files changed, and a clean
worktree.

- [ ] **Step 6: Merge, push, and verify production**

Fast-forward `main`, push `origin/main`, wait for the Vercel deployment to reach
`READY`, then repeat the duplicate, search, two-line-name, footer, overflow,
and console checks at:

```text
https://classic-hubble.vercel.app/composers
```
