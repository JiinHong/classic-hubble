# Composer Directory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dense `/composers` directory that lists every cataloged composer, supports period/search/sort controls, marks core composers lightly, and links into existing work and performance discovery.

**Architecture:** A committed composer-only snapshot from the public-domain Open Opus dataset provides a broad baseline without a runtime third-party dependency. The catalog layer merges Supabase rows over that baseline, then a server page passes normalized entries to one client directory component. Pure functions own period normalization, search, sorting, grouping, core marking, and link generation; the existing home search accepts the selected composer through the Next.js 16 `searchParams` promise.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5, Tailwind CSS 4, Supabase JS 2, Vitest 4, React Testing Library, Lucide React.

## Global Constraints

- The page route is `/composers`.
- The page has no marketing hero, portraits, birth/death years, biographies, rankings, or decorative composer cards.
- Every composer returned by the catalog is visible by default; no display limit or hidden secondary list is allowed.
- The visible period controls are `전체`, `중세`, `르네상스`, `바로크`, `고전`, `낭만`, `20세기`, and `현대`.
- Unknown period values remain available under `기타`.
- Korean names are primary; original-language names are secondary.
- Core composers use only heavier type and a textual `핵심` marker.
- The baseline contains at least 200 Open Opus composers and excludes portraits, works, and birth/death fields.
- Supabase rows override matching baseline composers by normalized original-language name.
- A missing Korean name falls back to the original name without rendering it twice.
- Desktop uses four columns, tablet uses two columns, and mobile uses one column.
- Implementation follows TDD: failing test, observed failure, minimal implementation, passing test, then commit.
- Do not add a dependency or change the Supabase schema for this feature.

---

## File Map

- Create `apps/web/src/data/openopus-composers.json`: composer-only public-domain baseline snapshot.
- Create `apps/web/src/data/openopus-composers.test.ts`: dataset integrity and scope test.
- Create `docs/data-sources.md`: source, license, endpoint, retained fields, and snapshot date.
- Create `apps/web/src/lib/composer-directory.ts`: pure composer normalization, search, sort, grouping, and link helpers.
- Create `apps/web/src/lib/composer-directory.test.ts`: unit coverage for every directory rule.
- Modify `apps/web/src/lib/catalog.ts`: merge paginated Supabase rows over the Open Opus baseline.
- Create `apps/web/src/lib/catalog.test.ts`: test pagination, merge precedence, and baseline fallback.
- Create `apps/web/src/components/ComposerPeriodFilter.tsx`: accessible period segmented control.
- Create `apps/web/src/components/ComposerListItem.tsx`: dense text-only composer link.
- Create `apps/web/src/components/ComposerList.tsx`: period headings and responsive columns.
- Create `apps/web/src/components/ComposerDirectory.tsx`: client search, period, sort, and result state.
- Create `apps/web/src/components/ComposerDirectory.test.tsx`: interaction and display tests.
- Create `apps/web/src/app/composers/page.tsx`: composer directory server route.
- Modify `apps/web/src/components/AppHeader.tsx`: add the `작곡가` navigation entry.
- Modify `apps/web/src/components/AppHeader.test.tsx`: assert the new accessible navigation link.
- Modify `apps/web/src/components/SearchExperience.tsx`: accept an initial composer query.
- Create `apps/web/src/components/SearchExperience.test.tsx`: verify composer deep-link filtering.
- Modify `apps/web/src/app/page.tsx`: read the Next.js 16 `searchParams` promise and pass the composer name to search.

---

### Task 1: Open Opus Baseline Snapshot

**Files:**
- Create: `apps/web/src/data/openopus-composers.json`
- Create: `apps/web/src/data/openopus-composers.test.ts`
- Create: `docs/data-sources.md`

**Interfaces:**
- Consumes: `https://api.openopus.org/work/dump.json`.
- Produces: an array of `{ name: string; nameKo: null; period: string }` entries with no runtime API dependency.

- [ ] **Step 1: Write the failing dataset integrity test**

```ts
import { describe, expect, it } from "vitest";

import composers from "./openopus-composers.json";

describe("Open Opus composer snapshot", () => {
  it("contains a broad, composer-only, unique baseline", () => {
    expect(composers.length).toBeGreaterThanOrEqual(200);
    expect(new Set(composers.map((composer) => composer.name)).size).toBe(
      composers.length,
    );
    const periods = new Set(composers.map((composer) => composer.period));
    for (const expectedPeriod of [
      "Medieval",
      "Renaissance",
      "Baroque",
      "Classical",
      "Early Romantic",
      "Romantic",
      "Late Romantic",
      "20th Century",
      "Post-War",
      "21st Century",
    ]) {
      expect(periods.has(expectedPeriod)).toBe(true);
    }
    expect(Object.keys(composers[0] ?? {}).sort()).toEqual([
      "name",
      "nameKo",
      "period",
    ]);
  });
});
```

- [ ] **Step 2: Run the data test and verify the missing JSON failure**

Run:

```bash
pnpm --filter web test -- src/data/openopus-composers.test.ts
```

Expected: FAIL because `openopus-composers.json` does not exist.

- [ ] **Step 3: Generate and inspect the composer-only snapshot**

Run from the repository root:

```bash
node --input-type=module -e 'import fs from "node:fs"; const response = await fetch("https://api.openopus.org/work/dump.json", { headers: { "User-Agent": "Classic-Hubble/0.1" } }); if (!response.ok) throw new Error(`Open Opus returned ${response.status}`); const payload = await response.json(); const composers = payload.composers.map((composer) => ({ name: composer.complete_name.trim(), nameKo: null, period: composer.epoch.trim() })).filter((composer) => composer.name && composer.period).sort((a, b) => a.name.localeCompare(b.name, "en")); if (new Set(composers.map((composer) => composer.name)).size !== composers.length) throw new Error("Open Opus composer names are not unique"); fs.mkdirSync("apps/web/src/data", { recursive: true }); fs.writeFileSync("apps/web/src/data/openopus-composers.json", `${JSON.stringify(composers, null, 2)}\n`);'
```

Expected: `apps/web/src/data/openopus-composers.json` contains at least 200 entries and each entry has only `name`, `nameKo`, and `period`.

- [ ] **Step 4: Add the data-source record**

Create `docs/data-sources.md`:

```markdown
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
```

- [ ] **Step 5: Run the dataset integrity test**

Run:

```bash
pnpm --filter web test -- src/data/openopus-composers.test.ts
```

Expected: PASS with 1 test.

- [ ] **Step 6: Commit the baseline snapshot**

```bash
git add apps/web/src/data/openopus-composers.json apps/web/src/data/openopus-composers.test.ts docs/data-sources.md
git commit -m "data: add Open Opus composer baseline"
```

---

### Task 2: Pure Composer Directory Rules

**Files:**
- Create: `apps/web/src/lib/composer-directory.ts`
- Test: `apps/web/src/lib/composer-directory.test.ts`

**Interfaces:**
- Consumes: raw composer fields `{ id, name, nameKo, period }`.
- Produces:
  - `ComposerPeriodKey`
  - `ComposerDirectoryEntry`
  - `ComposerDirectorySort`
  - `PERIOD_OPTIONS`
  - `toComposerDirectoryEntry(input)`
  - `filterAndSortComposers(entries, options)`
  - `groupComposers(entries)`
  - `composerDiscoveryHref(composer)`
  - `composerIdentityKey(name)`

- [ ] **Step 1: Write failing unit tests for normalization, filtering, sorting, grouping, and links**

```ts
import { describe, expect, it } from "vitest";

import {
  composerDiscoveryHref,
  composerIdentityKey,
  filterAndSortComposers,
  groupComposers,
  toComposerDirectoryEntry,
} from "./composer-directory";

const bach = toComposerDirectoryEntry({
  id: "bach",
  name: "Johann Sebastian Bach",
  nameKo: "요한 제바스티안 바흐",
  period: "Baroque",
});
const debussy = toComposerDirectoryEntry({
  id: "debussy",
  name: "Claude Debussy",
  nameKo: "클로드 드뷔시",
  period: "20th Century",
});
const unknown = toComposerDirectoryEntry({
  id: "unknown",
  name: "Unknown Composer",
  nameKo: null,
  period: null,
});

describe("composer directory rules", () => {
  it("normalizes period and derives core status", () => {
    expect(bach.period).toBe("baroque");
    expect(bach.isCore).toBe(true);
    expect(debussy.period).toBe("twentieth");
    expect(unknown.period).toBe("other");
    expect(unknown.nameKo).toBe("Unknown Composer");
    expect(
      toComposerDirectoryEntry({
        id: "adams",
        name: "John Adams",
        nameKo: null,
        period: "21st Century",
      }).period,
    ).toBe("contemporary");
    expect(
      toComposerDirectoryEntry({
        id: "haydn",
        name: "Franz Joseph Haydn",
        nameKo: null,
        period: "Classical",
      }),
    ).toMatchObject({ isCore: true, nameKo: "요제프 하이든" });
    expect(
      toComposerDirectoryEntry({
        id: "schnittke",
        name: "Alfred Schnittke",
        nameKo: null,
        period: "Post-War",
      }).period,
    ).toBe("contemporary");
  });

  it("searches Korean and original-language names", () => {
    const entries = [bach, debussy];

    expect(
      filterAndSortComposers(entries, {
        period: "all",
        query: "바흐",
        sort: "ko",
      }).map((entry) => entry.id),
    ).toEqual(["bach"]);
    expect(
      filterAndSortComposers(entries, {
        period: "all",
        query: "debussy",
        sort: "ko",
      }).map((entry) => entry.id),
    ).toEqual(["debussy"]);
  });

  it("filters periods and supports Korean and Latin sorting", () => {
    const entries = [debussy, bach];

    expect(
      filterAndSortComposers(entries, {
        period: "baroque",
        query: "",
        sort: "ko",
      }).map((entry) => entry.id),
    ).toEqual(["bach"]);
    expect(
      filterAndSortComposers(entries, {
        period: "all",
        query: "",
        sort: "latin",
      }).map((entry) => entry.id),
    ).toEqual(["debussy", "bach"]);
  });

  it("keeps period groups in musical chronology", () => {
    expect(groupComposers([unknown, debussy, bach]).map((group) => group.key)).toEqual([
      "baroque",
      "twentieth",
      "other",
    ]);
  });

  it("builds an encoded composer discovery link", () => {
    expect(composerDiscoveryHref(bach)).toBe(
      `/?composer=${encodeURIComponent("요한 제바스티안 바흐")}`,
    );
    expect(composerIdentityKey("Frédéric Chopin")).toBe("frederic chopin");
  });
});
```

- [ ] **Step 2: Run the unit test and verify the missing module failure**

Run:

```bash
pnpm --filter web test -- src/lib/composer-directory.test.ts
```

Expected: FAIL because `./composer-directory` does not exist.

- [ ] **Step 3: Implement the pure directory module**

```ts
export const PERIOD_OPTIONS = [
  { key: "all", label: "전체" },
  { key: "medieval", label: "중세" },
  { key: "renaissance", label: "르네상스" },
  { key: "baroque", label: "바로크" },
  { key: "classical", label: "고전" },
  { key: "romantic", label: "낭만" },
  { key: "twentieth", label: "20세기" },
  { key: "contemporary", label: "현대" },
] as const;

export type ComposerPeriodKey =
  | "medieval"
  | "renaissance"
  | "baroque"
  | "classical"
  | "romantic"
  | "twentieth"
  | "contemporary"
  | "other";

export type ComposerDirectorySort = "ko" | "latin";

export type ComposerDirectoryEntry = {
  id: string;
  isCore: boolean;
  name: string;
  nameKo: string;
  period: ComposerPeriodKey;
};

type RawComposer = {
  id: string;
  name: string;
  nameKo: string | null;
  period: string | null;
};

type DirectoryOptions = {
  period: "all" | ComposerPeriodKey;
  query: string;
  sort: ComposerDirectorySort;
};

const PERIOD_ORDER: ComposerPeriodKey[] = [
  "medieval",
  "renaissance",
  "baroque",
  "classical",
  "romantic",
  "twentieth",
  "contemporary",
  "other",
];

const PERIOD_LABELS: Record<ComposerPeriodKey, string> = {
  baroque: "바로크",
  classical: "고전",
  contemporary: "현대",
  medieval: "중세",
  other: "기타",
  renaissance: "르네상스",
  romantic: "낭만",
  twentieth: "20세기",
};

const CORE_COMPOSER_LABELS = new Map(
  (
    [
      ["Antonio Vivaldi", "안토니오 비발디"],
      ["Johann Sebastian Bach", "요한 제바스티안 바흐"],
      ["George Frideric Handel", "게오르크 프리드리히 헨델"],
      ["Franz Joseph Haydn", "요제프 하이든"],
      ["Wolfgang Amadeus Mozart", "볼프강 아마데우스 모차르트"],
      ["Ludwig van Beethoven", "루트비히 판 베토벤"],
      ["Franz Schubert", "프란츠 슈베르트"],
      ["Robert Schumann", "로베르트 슈만"],
      ["Frédéric Chopin", "프레데리크 쇼팽"],
      ["Franz Liszt", "프란츠 리스트"],
      ["Richard Wagner", "리하르트 바그너"],
      ["Johannes Brahms", "요하네스 브람스"],
      ["Pyotr Ilyich Tchaikovsky", "표트르 일리치 차이콥스키"],
      ["Antonín Dvořák", "안토닌 드보르자크"],
      ["Gustav Mahler", "구스타프 말러"],
      ["Claude Debussy", "클로드 드뷔시"],
      ["Maurice Ravel", "모리스 라벨"],
      ["Sergei Rachmaninoff", "세르게이 라흐마니노프"],
      ["Igor Stravinsky", "이고르 스트라빈스키"],
      ["Dmitri Shostakovich", "드미트리 쇼스타코비치"],
    ] as const
  ).map(([name, nameKo]) => [normalizeText(name), nameKo]),
);

function normalizeText(value: string) {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase()
    .trim();
}

function normalizePeriod(value: string | null): ComposerPeriodKey {
  const period = normalizeText(value ?? "");
  if (period.includes("medieval") || period.includes("중세")) return "medieval";
  if (period.includes("renaissance") || period.includes("르네상스")) {
    return "renaissance";
  }
  if (period.includes("baroque") || period.includes("바로크")) return "baroque";
  if (period.includes("classical") || period.includes("고전")) return "classical";
  if (period.includes("romantic") || period.includes("낭만")) return "romantic";
  if (
    period.includes("20th") ||
    period.includes("modern") ||
    period.includes("20세기") ||
    period.includes("근현대")
  ) {
    return "twentieth";
  }
  if (
    period.includes("contemporary") ||
    period.includes("post-war") ||
    period.includes("21st century") ||
    period.includes("현대")
  ) {
    return "contemporary";
  }
  return "other";
}

export function toComposerDirectoryEntry(input: RawComposer): ComposerDirectoryEntry {
  const identityKey = normalizeText(input.name);

  return {
    id: input.id,
    isCore: CORE_COMPOSER_LABELS.has(identityKey),
    name: input.name.trim(),
    nameKo:
      input.nameKo?.trim() ||
      CORE_COMPOSER_LABELS.get(identityKey) ||
      input.name.trim(),
    period: normalizePeriod(input.period),
  };
}

export function filterAndSortComposers(
  entries: ComposerDirectoryEntry[],
  options: DirectoryOptions,
) {
  const query = normalizeText(options.query);
  const locale = options.sort === "ko" ? "ko-KR" : "en";
  const collator = new Intl.Collator(locale, { sensitivity: "base" });

  return entries
    .filter((entry) => options.period === "all" || entry.period === options.period)
    .filter((entry) => {
      if (!query) return true;
      return normalizeText(`${entry.nameKo} ${entry.name}`).includes(query);
    })
    .toSorted((a, b) =>
      collator.compare(
        options.sort === "ko" ? a.nameKo : a.name,
        options.sort === "ko" ? b.nameKo : b.name,
      ),
    );
}

export function groupComposers(entries: ComposerDirectoryEntry[]) {
  return PERIOD_ORDER.map((key) => ({
    composers: entries.filter((entry) => entry.period === key),
    key,
    label: PERIOD_LABELS[key],
  })).filter((group) => group.composers.length > 0);
}

export function composerDiscoveryHref(
  composer: Pick<ComposerDirectoryEntry, "name" | "nameKo">,
) {
  return `/?composer=${encodeURIComponent(composer.nameKo || composer.name)}`;
}

export function composerIdentityKey(name: string) {
  return normalizeText(name);
}
```

- [ ] **Step 4: Run the unit test and verify it passes**

Run:

```bash
pnpm --filter web test -- src/lib/composer-directory.test.ts
```

Expected: PASS with 5 tests.

- [ ] **Step 5: Commit the pure directory rules**

```bash
git add apps/web/src/lib/composer-directory.ts apps/web/src/lib/composer-directory.test.ts
git commit -m "feat(web): add composer directory rules"
```

---

### Task 3: Composer Catalog Loader

**Files:**
- Modify: `apps/web/src/lib/catalog.ts`
- Create: `apps/web/src/lib/catalog.test.ts`

**Interfaces:**
- Consumes: the Open Opus snapshot from Task 1, `toComposerDirectoryEntry()` from Task 2, and Supabase `composers` rows.
- Produces: `getComposerDirectory(): Promise<ComposerDirectoryEntry[]>`.

- [ ] **Step 1: Write failing tests for remote rows and local fallback**

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import openOpusComposers from "@/data/openopus-composers.json";

const mocks = vi.hoisted(() => ({
  configured: { value: true },
  createSupabaseClient: vi.fn(),
}));

vi.mock("./supabase/client", () => ({
  createSupabaseClient: () => mocks.createSupabaseClient(),
  get isSupabaseConfigured() {
    return mocks.configured.value;
  },
}));

describe("getComposerDirectory", () => {
  afterEach(() => {
    mocks.configured.value = true;
    mocks.createSupabaseClient.mockReset();
    vi.resetModules();
  });

  it("loads every Supabase page without imposing a display limit", async () => {
    const firstPage = Array.from({ length: 1000 }, (_, index) => ({
      id: `composer-${index}`,
      name: `Composer ${index}`,
      name_ko: `작곡가 ${index}`,
      period: "Baroque",
    }));
    const range = vi
      .fn()
      .mockResolvedValueOnce({ data: firstPage, error: null })
      .mockResolvedValueOnce({
        data: [
          {
            id: "debussy",
            name: "Claude Debussy",
            name_ko: "클로드 드뷔시",
            period: "20th Century",
          },
        ],
        error: null,
      });
    const order = vi.fn(() => ({ range }));
    mocks.createSupabaseClient.mockReturnValue({
      from: vi.fn(() => ({ select: vi.fn(() => ({ order })) })),
    });

    const { getComposerDirectory } = await import("./catalog");
    const composers = await getComposerDirectory();

    expect(composers).toHaveLength(openOpusComposers.length + 1000);
    expect(
      composers.find((composer) => composer.name === "Claude Debussy"),
    ).toMatchObject({
      nameKo: "클로드 드뷔시",
      period: "twentieth",
    });
    expect(range).toHaveBeenNthCalledWith(1, 0, 999);
    expect(range).toHaveBeenNthCalledWith(2, 1000, 1999);
  });

  it("returns the complete baseline when Supabase is unavailable", async () => {
    mocks.configured.value = false;

    const { getComposerDirectory } = await import("./catalog");
    const composers = await getComposerDirectory();

    expect(new Set(composers.map((composer) => composer.name)).size).toBe(
      composers.length,
    );
    expect(composers).toHaveLength(openOpusComposers.length);
  });
});
```

- [ ] **Step 2: Run the catalog test and verify the missing export**

Run:

```bash
pnpm --filter web test -- src/lib/catalog.test.ts
```

Expected: FAIL because `getComposerDirectory` is not exported.

- [ ] **Step 3: Add baseline merging and the paginated Supabase query**

Add the directory import and row type:

```ts
import openOpusComposers from "@/data/openopus-composers.json";

import {
  composerIdentityKey,
  toComposerDirectoryEntry,
  type ComposerDirectoryEntry,
} from "./composer-directory";

type ComposerDirectoryRow = {
  id: string;
  name: string;
  name_ko: string | null;
  period: string | null;
};
```

Add the baseline mapper and merge function near `fallbackSnapshot`:

```ts
const baselineComposerDirectory = openOpusComposers.map((composer) =>
  toComposerDirectoryEntry({
    id: `openopus:${composerIdentityKey(composer.name)}`,
    name: composer.name,
    nameKo: composer.nameKo,
    period: composer.period,
  }),
);

function mergeComposerRows(
  rows: ComposerDirectoryRow[],
): ComposerDirectoryEntry[] {
  const composersByName = new Map(
    baselineComposerDirectory.map((composer) => [
      composerIdentityKey(composer.name),
      composer,
    ]),
  );

  for (const row of rows) {
    composersByName.set(
      composerIdentityKey(row.name),
      toComposerDirectoryEntry({
        id: row.id,
        name: row.name,
        nameKo: row.name_ko,
        period: row.period,
      }),
    );
  }

  return Array.from(composersByName.values());
}
```

Add the public loader:

```ts
const COMPOSER_PAGE_SIZE = 1000;

export async function getComposerDirectory(): Promise<ComposerDirectoryEntry[]> {
  if (!isSupabaseConfigured) return baselineComposerDirectory;

  try {
    const supabase = createSupabaseClient();
    const rows: ComposerDirectoryRow[] = [];

    for (let offset = 0; ; offset += COMPOSER_PAGE_SIZE) {
      const result = await supabase
        .from("composers")
        .select("id, name, name_ko, period")
        .order("name_ko", { ascending: true, nullsFirst: false })
        .range(offset, offset + COMPOSER_PAGE_SIZE - 1);

      if (result.error) return baselineComposerDirectory;

      const page = (result.data ?? []) as ComposerDirectoryRow[];
      rows.push(...page);
      if (page.length < COMPOSER_PAGE_SIZE) break;
    }

    return mergeComposerRows(rows);
  } catch {
    return baselineComposerDirectory;
  }
}
```

- [ ] **Step 4: Run the catalog tests and the existing web tests**

Run:

```bash
pnpm --filter web test -- src/lib/catalog.test.ts src/lib/composer-directory.test.ts
```

Expected: PASS with 7 tests.

- [ ] **Step 5: Commit the loader**

```bash
git add apps/web/src/lib/catalog.ts apps/web/src/lib/catalog.test.ts
git commit -m "feat(web): load composer directory catalog"
```

---

### Task 4: Dense Composer Directory UI

**Files:**
- Create: `apps/web/src/components/ComposerPeriodFilter.tsx`
- Create: `apps/web/src/components/ComposerListItem.tsx`
- Create: `apps/web/src/components/ComposerList.tsx`
- Create: `apps/web/src/components/ComposerDirectory.tsx`
- Create: `apps/web/src/components/ComposerDirectory.test.tsx`

**Interfaces:**
- Consumes: `ComposerDirectoryEntry[]`, `PERIOD_OPTIONS`, `filterAndSortComposers()`, `groupComposers()`, and `composerDiscoveryHref()`.
- Produces: `<ComposerDirectory composers={composers} />`.

- [ ] **Step 1: Write failing interaction tests**

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { toComposerDirectoryEntry } from "@/lib/composer-directory";

import { ComposerDirectory } from "./ComposerDirectory";

const composers = [
  toComposerDirectoryEntry({
    id: "bach",
    name: "Johann Sebastian Bach",
    nameKo: "요한 제바스티안 바흐",
    period: "Baroque",
  }),
  toComposerDirectoryEntry({
    id: "vivaldi",
    name: "Antonio Vivaldi",
    nameKo: "안토니오 비발디",
    period: "Baroque",
  }),
  toComposerDirectoryEntry({
    id: "debussy",
    name: "Claude Debussy",
    nameKo: "클로드 드뷔시",
    period: "20th Century",
  }),
];

describe("ComposerDirectory", () => {
  it("shows all composers with Korean and original names", () => {
    render(<ComposerDirectory composers={composers} />);

    expect(screen.getByText("3명의 작곡가")).toBeTruthy();
    expect(screen.getByText("요한 제바스티안 바흐")).toBeTruthy();
    expect(screen.getByText("Johann Sebastian Bach")).toBeTruthy();
  });

  it("searches and filters without hiding the other period permanently", () => {
    render(<ComposerDirectory composers={composers} />);

    fireEvent.change(screen.getByLabelText("작곡가 이름 검색"), {
      target: { value: "Debussy" },
    });
    expect(screen.getByText("1명의 작곡가")).toBeTruthy();
    expect(screen.queryByText("안토니오 비발디")).toBeNull();

    fireEvent.change(screen.getByLabelText("작곡가 이름 검색"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "바로크" }));
    expect(screen.getByText("2명의 작곡가")).toBeTruthy();
    expect(screen.queryByText("클로드 드뷔시")).toBeNull();
  });

  it("marks core composers and links them to discovery", () => {
    render(<ComposerDirectory composers={composers} />);

    expect(screen.getAllByText("핵심").length).toBeGreaterThan(0);
    expect(
      screen
        .getByRole("link", { name: /요한 제바스티안 바흐/ })
        .getAttribute("href"),
    ).toBe(`/?composer=${encodeURIComponent("요한 제바스티안 바흐")}`);
  });

  it("switches the visible list to original-language order", () => {
    render(<ComposerDirectory composers={composers} />);

    expect(screen.getAllByRole("link")[1]?.textContent).toContain(
      "Johann Sebastian Bach",
    );
    fireEvent.click(screen.getByRole("button", { name: "A–Z" }));
    expect(screen.getAllByRole("link")[1]?.textContent).toContain("Claude Debussy");
  });

  it("shows an explicit no-results state", () => {
    render(<ComposerDirectory composers={composers} />);

    fireEvent.change(screen.getByLabelText("작곡가 이름 검색"), {
      target: { value: "없는 작곡가" },
    });
    expect(screen.getByText("조건에 맞는 작곡가가 없습니다")).toBeTruthy();
  });

  it("distinguishes a catalog load failure from a filtered empty list", () => {
    render(<ComposerDirectory composers={[]} />);

    expect(screen.getByText("작곡가 데이터를 불러오지 못했습니다")).toBeTruthy();
    expect(screen.getByRole("link", { name: "다시 시도" }).getAttribute("href")).toBe(
      "/composers",
    );
  });

  it("does not duplicate an original name when no Korean label exists", () => {
    render(
      <ComposerDirectory
        composers={[
          toComposerDirectoryEntry({
            id: "adams",
            name: "John Adams",
            nameKo: null,
            period: "21st Century",
          }),
        ]}
      />,
    );

    expect(screen.getAllByText("John Adams")).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run the component test and verify the missing component failure**

Run:

```bash
pnpm --filter web test -- src/components/ComposerDirectory.test.tsx
```

Expected: FAIL because `ComposerDirectory` does not exist.

- [ ] **Step 3: Implement the period segmented control**

```tsx
import {
  PERIOD_OPTIONS,
  type ComposerPeriodKey,
} from "@/lib/composer-directory";

type ComposerPeriodFilterProps = {
  onChange: (period: "all" | ComposerPeriodKey) => void;
  value: "all" | ComposerPeriodKey;
};

export function ComposerPeriodFilter({
  onChange,
  value,
}: ComposerPeriodFilterProps) {
  return (
    <div aria-label="시대" className="flex overflow-x-auto border-y border-stone-200">
      {PERIOD_OPTIONS.map((option) => (
        <button
          aria-pressed={value === option.key}
          className={`h-11 shrink-0 border-r border-stone-200 px-4 text-sm font-bold transition ${
            value === option.key
              ? "bg-stone-950 text-white"
              : "bg-white text-stone-600 hover:bg-stone-100 hover:text-stone-950"
          }`}
          key={option.key}
          onClick={() => onChange(option.key)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Implement text-only list items and period groups**

`ComposerListItem.tsx`:

```tsx
import Link from "next/link";

import {
  composerDiscoveryHref,
  type ComposerDirectoryEntry,
} from "@/lib/composer-directory";

export function ComposerListItem({
  composer,
}: {
  composer: ComposerDirectoryEntry;
}) {
  return (
    <li className="border-b border-stone-200">
      <Link
        className="group block min-h-16 py-3 outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 focus-visible:ring-offset-2"
        href={composerDiscoveryHref(composer)}
      >
        <span className="flex items-center gap-2">
          <span
            className={`text-sm text-stone-950 ${
              composer.isCore ? "font-black" : "font-bold"
            }`}
          >
            {composer.nameKo}
          </span>
          {composer.isCore ? (
            <span className="border border-rose-200 bg-rose-50 px-1.5 py-0.5 text-[10px] font-black text-rose-700">
              핵심
            </span>
          ) : null}
        </span>
        {composer.nameKo !== composer.name ? (
          <span className="mt-1 block text-xs text-stone-500 group-hover:text-emerald-800">
            {composer.name}
          </span>
        ) : null}
      </Link>
    </li>
  );
}
```

`ComposerList.tsx`:

```tsx
import {
  groupComposers,
  type ComposerDirectoryEntry,
} from "@/lib/composer-directory";

import { ComposerListItem } from "./ComposerListItem";

export function ComposerList({
  composers,
}: {
  composers: ComposerDirectoryEntry[];
}) {
  return (
    <div className="space-y-10">
      {groupComposers(composers).map((group) => (
        <section aria-labelledby={`period-${group.key}`} key={group.key}>
          <div className="mb-2 flex items-baseline justify-between border-b-2 border-stone-950 pb-2">
            <h2 className="text-lg font-black text-stone-950" id={`period-${group.key}`}>
              {group.label}
            </h2>
            <span className="text-xs font-bold text-stone-500">
              {group.composers.length}명
            </span>
          </div>
          <ul className="grid grid-cols-1 gap-x-6 sm:grid-cols-2 xl:grid-cols-4">
            {group.composers.map((composer) => (
              <ComposerListItem composer={composer} key={composer.id} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Implement directory state, search, sort, count, and empty state**

```tsx
"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import {
  filterAndSortComposers,
  type ComposerDirectoryEntry,
  type ComposerDirectorySort,
  type ComposerPeriodKey,
} from "@/lib/composer-directory";

import { ComposerList } from "./ComposerList";
import { ComposerPeriodFilter } from "./ComposerPeriodFilter";

export function ComposerDirectory({
  composers,
}: {
  composers: ComposerDirectoryEntry[];
}) {
  const [period, setPeriod] = useState<"all" | ComposerPeriodKey>("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<ComposerDirectorySort>("ko");

  const visibleComposers = useMemo(
    () => filterAndSortComposers(composers, { period, query, sort }),
    [composers, period, query, sort],
  );

  if (composers.length === 0) {
    return (
      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-black text-stone-950">작곡가</h1>
        <p className="mt-8 border-y border-stone-200 py-12 text-center text-sm font-bold text-stone-500">
          작곡가 데이터를 불러오지 못했습니다
        </p>
        <div className="mt-4 text-center">
          <Link className="text-sm font-black text-emerald-800 underline" href="/composers">
            다시 시도
          </Link>
        </div>
      </section>
    );
  }

  return (
    <>
      <section className="border-b border-stone-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-7 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl font-black text-stone-950">작곡가</h1>
              <p aria-live="polite" className="mt-1 text-sm font-bold text-stone-500">
                {visibleComposers.length}명의 작곡가
              </p>
            </div>
            <div className="grid grid-cols-2 border border-stone-200 bg-stone-100 p-1">
              {(["ko", "latin"] as const).map((option) => (
                <button
                  aria-pressed={sort === option}
                  className={`h-9 px-3 text-sm font-black ${
                    sort === option ? "bg-white text-stone-950 shadow-sm" : "text-stone-500"
                  }`}
                  key={option}
                  onClick={() => setSort(option)}
                  type="button"
                >
                  {option === "ko" ? "가나다순" : "A–Z"}
                </button>
              ))}
            </div>
          </div>

          <label className="mt-6 block text-sm font-black text-stone-800" htmlFor="composer-search">
            작곡가 이름 검색
          </label>
          <div className="relative mt-2">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 size-5 -translate-y-1/2 text-stone-400"
            />
            <input
              className="h-12 w-full border border-stone-300 bg-white pl-10 pr-3 font-semibold text-stone-950 outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
              id="composer-search"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="한글 또는 원어 이름"
              type="search"
              value={query}
            />
          </div>
        </div>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <ComposerPeriodFilter onChange={setPeriod} value={period} />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {visibleComposers.length ? (
          <ComposerList composers={visibleComposers} />
        ) : (
          <p className="border-y border-stone-200 py-14 text-center text-sm font-bold text-stone-500">
            조건에 맞는 작곡가가 없습니다
          </p>
        )}
      </section>
    </>
  );
}
```

- [ ] **Step 6: Run the component and pure tests**

Run:

```bash
pnpm --filter web test -- src/components/ComposerDirectory.test.tsx src/lib/composer-directory.test.ts
```

Expected: PASS with 12 tests.

- [ ] **Step 7: Commit the UI**

```bash
git add apps/web/src/components/ComposerDirectory.tsx apps/web/src/components/ComposerDirectory.test.tsx apps/web/src/components/ComposerPeriodFilter.tsx apps/web/src/components/ComposerList.tsx apps/web/src/components/ComposerListItem.tsx
git commit -m "feat(web): build dense composer directory"
```

---

### Task 5: Route and Primary Navigation

**Files:**
- Create: `apps/web/src/app/composers/page.tsx`
- Modify: `apps/web/src/components/AppHeader.tsx`
- Modify: `apps/web/src/components/AppHeader.test.tsx`

**Interfaces:**
- Consumes: `getComposerDirectory()` and `<ComposerDirectory composers={...} />`.
- Produces: public `/composers` page and accessible `작곡가` header link.

- [ ] **Step 1: Extend the header test with the missing composer link assertion**

Add to `keeps icon-only mobile navigation links named`:

```tsx
expect(screen.getByRole("link", { name: "작곡가" }).getAttribute("href")).toBe(
  "/composers",
);
```

- [ ] **Step 2: Run the header test and observe the failure**

Run:

```bash
pnpm --filter web test -- src/components/AppHeader.test.tsx
```

Expected: FAIL because no `작곡가` link exists.

- [ ] **Step 3: Add the navigation entry and composer route**

In `AppHeader.tsx`, import `LibraryBig` from Lucide and add:

```ts
const navigation = [
  { href: "/", label: "탐색", icon: Search },
  { href: "/composers", label: "작곡가", icon: LibraryBig },
  { href: "/watchlist", label: "관심곡", icon: Bell },
  { href: "/admin/review", label: "검수", icon: Settings2 },
];
```

Create `apps/web/src/app/composers/page.tsx`:

```tsx
import { ComposerDirectory } from "@/components/ComposerDirectory";
import { getComposerDirectory } from "@/lib/catalog";

export default async function ComposersPage() {
  const composers = await getComposerDirectory();
  return (
    <main>
      <ComposerDirectory composers={composers} />
    </main>
  );
}
```

- [ ] **Step 4: Run header and directory tests**

Run:

```bash
pnpm --filter web test -- src/components/AppHeader.test.tsx src/components/ComposerDirectory.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit the route and navigation**

```bash
git add apps/web/src/app/composers/page.tsx apps/web/src/components/AppHeader.tsx apps/web/src/components/AppHeader.test.tsx
git commit -m "feat(web): expose composer directory route"
```

---

### Task 6: Composer-to-Discovery Deep Link

**Files:**
- Modify: `apps/web/src/components/SearchExperience.tsx`
- Create: `apps/web/src/components/SearchExperience.test.tsx`
- Modify: `apps/web/src/app/page.tsx`

**Interfaces:**
- Consumes: `/?composer=<encoded-name>` generated by Task 2.
- Produces: `SearchExperienceProps.initialQuery?: string` and a home page that awaits `searchParams`.

- [ ] **Step 1: Write a failing initial-query component test**

```tsx
import { performances, works } from "@classic-hubble/shared";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SearchExperience } from "./SearchExperience";

describe("SearchExperience composer deep link", () => {
  it("starts with the composer query and filters matching works", () => {
    render(
      <SearchExperience
        initialQuery="세르게이 라흐마니노프"
        performances={performances}
        works={works}
      />,
    );

    expect(
      (screen.getByLabelText("곡명, 작곡가, 공연장 검색") as HTMLInputElement)
        .value,
    ).toBe("세르게이 라흐마니노프");
    expect(screen.getByText("1개 작품 매칭")).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run the test and observe the prop/type failure**

Run:

```bash
pnpm --filter web test -- src/components/SearchExperience.test.tsx
```

Expected: FAIL because `initialQuery` is not a supported prop.

- [ ] **Step 3: Add the initial query prop to SearchExperience**

```tsx
type SearchExperienceProps = {
  initialQuery?: string;
  performances: Performance[];
  works: Work[];
};

export function SearchExperience({
  initialQuery = "",
  performances,
  works,
}: SearchExperienceProps) {
  const [query, setQuery] = useState(initialQuery);
```

- [ ] **Step 4: Await the Next.js 16 searchParams promise in the home page**

Change the home page signature and pass the safe scalar:

```tsx
type HomeProps = {
  searchParams: Promise<{ composer?: string | string[] }>;
};

export default async function Home({ searchParams }: HomeProps) {
  const composerParam = (await searchParams).composer;
  const initialComposerQuery =
    typeof composerParam === "string" ? composerParam : (composerParam?.[0] ?? "");
  const catalog = await getCatalogSnapshot();
```

Pass it into the current component:

```tsx
<SearchExperience
  initialQuery={initialComposerQuery}
  performances={catalog.performances}
  works={catalog.works}
/>
```

- [ ] **Step 5: Run the deep-link and complete web test suite**

Run:

```bash
pnpm --filter web test
```

Expected: all web tests PASS.

- [ ] **Step 6: Commit the deep link**

```bash
git add apps/web/src/app/page.tsx apps/web/src/components/SearchExperience.tsx apps/web/src/components/SearchExperience.test.tsx
git commit -m "feat(web): connect composers to discovery search"
```

---

### Task 7: Full Verification and Browser QA

**Files:**
- Modify only if verification reveals a defect in files owned by Tasks 1–5.

**Interfaces:**
- Consumes: completed `/composers` flow.
- Produces: verified tests, lint, build, and responsive browser evidence.

- [ ] **Step 1: Run the full web test suite**

Run:

```bash
pnpm --filter web test
```

Expected: exit code 0 and all tests PASS.

- [ ] **Step 2: Run lint**

Run:

```bash
pnpm --filter web lint
```

Expected: exit code 0 with no ESLint errors.

- [ ] **Step 3: Run the production build**

Run:

```bash
pnpm --filter web build
```

Expected: exit code 0; Next.js lists `/composers` as a built route.

- [ ] **Step 4: Start the development server**

Run:

```bash
pnpm --filter web dev
```

Expected: server reports a local URL. Keep the process running for browser QA.

- [ ] **Step 5: Verify desktop behavior**

Open `/composers` at 1440×900 and verify:

- no hero, portrait, date, or decorative card appears;
- the default count is at least 220 and equals the merged catalog size;
- the list uses four columns at `xl`;
- search works for one Korean and one original-language name;
- period buttons update count and visible groups;
- `핵심` does not change row dimensions;
- a composer link opens the home page with the search prefilled.

- [ ] **Step 6: Verify mobile behavior**

Open `/composers` at 390×844 and verify:

- the page has no horizontal document overflow;
- period controls scroll horizontally without wrapping;
- composer entries use one column;
- Korean and original names fit without overlap;
- search, sort, and composer links remain keyboard/touch accessible.

- [ ] **Step 7: Inspect repository state**

Run:

```bash
git status --short
```

Expected: clean worktree. If browser QA required a fix, commit only the scoped fix with:

```bash
git add apps/web/src
git commit -m "fix(web): polish composer directory"
```
