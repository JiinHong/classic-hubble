import { afterEach, describe, expect, it, vi } from "vitest";
import { randomBytes } from "node:crypto";
import { gunzipSync } from "node:zlib";

import openOpusComposers from "@/data/openopus-composers.json";

const mocks = vi.hoisted(() => ({
  configured: { value: true },
  createSupabaseClient: vi.fn(),
  cacheReads: vi.fn(),
  persistent: new Map<string, { expires: number; value: unknown }>(),
}));

vi.mock("next/cache", () => ({
  unstable_cache:
    (
      read: (...args: unknown[]) => Promise<unknown>,
      keys: string[],
      options: { revalidate: number },
    ) =>
    async (...args: unknown[]) => {
      mocks.cacheReads(keys);
      const key = JSON.stringify([keys, args]);
      const cached = mocks.persistent.get(key);
      if (cached && cached.expires > Date.now()) return cached.value;
      const value = await read(...args);
      mocks.persistent.set(key, {
        expires: Date.now() + options.revalidate * 1000,
        value,
      });
      return value;
    },
}));
afterEach(() => mocks.persistent.clear());

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

  it("reuses public composer rows across successive page visits", async () => {
    const range = vi.fn().mockResolvedValue({ data: [], error: null });
    const query = { order: vi.fn(() => query), range };
    mocks.createSupabaseClient.mockReturnValue({
      from: () => ({ select: () => query }),
    });
    const { getComposerDirectory } = await import("./catalog");
    await getComposerDirectory();
    await getComposerDirectory();
    expect(range).toHaveBeenCalledTimes(1);
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
    const order = vi.fn((column: string) =>
      column === "name_ko" ? { order } : { range },
    );
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
    expect(order).toHaveBeenNthCalledWith(1, "name_ko", {
      ascending: true,
      nullsFirst: false,
    });
    expect(order).toHaveBeenNthCalledWith(2, "id", { ascending: true });
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

  it("returns pristine baseline entries after a caller mutates a fallback result", async () => {
    mocks.configured.value = false;

    const { getComposerDirectory } = await import("./catalog");
    const firstResult = await getComposerDirectory();
    firstResult[0].name = "Mutated Composer";

    const secondResult = await getComposerDirectory();

    expect(secondResult[0].name).toBe(openOpusComposers[0].name);
  });

  it("requests an empty terminal page after an exact full page", async () => {
    const firstPage = Array.from({ length: 1000 }, (_, index) => ({
      id: `composer-${index}`,
      name: `Composer ${index}`,
      name_ko: null,
      period: "Baroque",
    }));
    const range = vi
      .fn()
      .mockResolvedValueOnce({ data: firstPage, error: null })
      .mockResolvedValueOnce({ data: [], error: null });
    const order = vi.fn((column: string) =>
      column === "name_ko" ? { order } : { range },
    );
    mocks.createSupabaseClient.mockReturnValue({
      from: vi.fn(() => ({ select: vi.fn(() => ({ order })) })),
    });

    const { getComposerDirectory } = await import("./catalog");
    const composers = await getComposerDirectory();

    expect(composers).toHaveLength(openOpusComposers.length + 1000);
    expect(range).toHaveBeenNthCalledWith(1, 0, 999);
    expect(range).toHaveBeenNthCalledWith(2, 1000, 1999);
  });

  it("returns the complete baseline when a Supabase query reports an error", async () => {
    const range = vi.fn().mockResolvedValue({
      data: null,
      error: new Error("query failed"),
    });
    const order = vi.fn((column: string) =>
      column === "name_ko" ? { order } : { range },
    );
    mocks.createSupabaseClient.mockReturnValue({
      from: vi.fn(() => ({ select: vi.fn(() => ({ order })) })),
    });

    const { getComposerDirectory } = await import("./catalog");
    const composers = await getComposerDirectory();

    expect(composers).toHaveLength(openOpusComposers.length);
  });

  it("returns the complete baseline when a Supabase query rejects", async () => {
    const range = vi.fn().mockRejectedValue(new Error("transport failed"));
    const order = vi.fn((column: string) =>
      column === "name_ko" ? { order } : { range },
    );
    mocks.createSupabaseClient.mockReturnValue({
      from: vi.fn(() => ({ select: vi.fn(() => ({ order })) })),
    });

    const { getComposerDirectory } = await import("./catalog");
    const composers = await getComposerDirectory();

    expect(composers).toHaveLength(openOpusComposers.length);
  });
});

describe("getCatalogSnapshot", () => {
  afterEach(() => {
    vi.useRealTimers();
    mocks.configured.value = true;
    mocks.createSupabaseClient.mockReset();
    vi.resetModules();
  });

  function database(pages: Record<string, unknown[][]>, failedTable?: string) {
    const ranges: Record<string, ReturnType<typeof vi.fn>> = {};
    const from = vi.fn((table: string) => {
      const range = (ranges[table] ??= vi.fn(async (start: number) => ({
        data: pages[table]?.[start / 1000] ?? [],
        error: failedTable === table ? new Error("unavailable") : null,
      })));
      const query = { order: vi.fn(() => query), range };
      return { select: vi.fn(() => query) };
    });
    mocks.createSupabaseClient.mockReturnValue({ from });
    return ranges;
  }

  const performance = (id: string) => ({
    kopis_performance_id: id,
    title: id,
    starts_at: "2026-12-01T10:00:00Z",
    status: "upcoming",
    program_items: [],
  });

  it("reuses public database pages even after the process-local catalog is recreated", async () => {
    const ranges = database({ performances: [[performance("p")]] });
    const first = await import("./catalog");
    await first.getCatalogSnapshot();
    mocks.cacheReads.mockClear();
    vi.resetModules();
    const second = await import("./catalog");
    expect((await second.getCatalogSnapshot()).performances[0].id).toBe("p");
    expect(ranges.works).toHaveBeenCalledTimes(1);
    expect(ranges.performances).toHaveBeenCalledTimes(1);
    expect(mocks.cacheReads).toHaveBeenCalledTimes(2);
    const entries = [...mocks.persistent].filter(([key]) =>
      key.includes("public-catalog-group"),
    );
    expect(entries).toHaveLength(2);
    expect(
      entries.map(([, { value }]) =>
        JSON.parse(
          gunzipSync(Buffer.from(value as string, "base64")).toString(),
        ),
      ),
    ).toContainEqual([performance("p")]);
  });

  it("falls back to bounded pages when the compressed snapshot exceeds the cache limit", async () => {
    const title = randomBytes(2_000_000).toString("base64");
    database({ performances: [[{ ...performance("large"), title }]] });
    const { getCatalogSnapshot } = await import("./catalog");
    const result = await getCatalogSnapshot();
    expect(result.source).toBe("supabase");
    expect(result.performances[0].title).toBe(title);
    const entry = [...mocks.persistent].find(
      ([key]) =>
        key.includes("public-catalog-group") && key.includes("performances"),
    );
    expect(entry?.[1].value).toBeNull();
  });

  it("reuses public catalog reads for one minute and coalesces simultaneous loads", async () => {
    vi.useFakeTimers();
    const ranges = database({ performances: [[performance("p")]] });
    const { getCatalogSnapshot } = await import("./catalog");
    const [first, second] = await Promise.all([
      getCatalogSnapshot(),
      getCatalogSnapshot(),
    ]);
    expect(first).toEqual(second);
    await getCatalogSnapshot();
    expect(ranges.works).toHaveBeenCalledTimes(1);
    expect(ranges.performances).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(60_001);
    await getCatalogSnapshot();
    expect(ranges.works).toHaveBeenCalledTimes(2);
  });

  it("retries unavailable catalog reads instead of caching an outage", async () => {
    database({}, "performances");
    const { getCatalogSnapshot } = await import("./catalog");
    expect((await getCatalogSnapshot()).source).toBe("unavailable");
    database({ performances: [[performance("recovered")]] });
    expect((await getCatalogSnapshot()).performances[0].id).toBe("recovered");
  });

  it("never replaces a missing configuration with fictional performances", async () => {
    mocks.configured.value = false;
    const { getCatalogSnapshot } = await import("./catalog");
    expect(await getCatalogSnapshot()).toMatchObject({
      performances: [],
      works: [],
      reviewQueue: [],
      source: "unavailable",
    });
  });

  it("loads performances beyond the first API page even with an empty work catalog", async () => {
    const ranges = database({
      performances: [
        Array.from({ length: 1000 }, (_, i) => performance(`p${i}`)),
        [performance("last")],
      ],
      works: [[]],
    });
    const { getCatalogSnapshot } = await import("./catalog");
    const result = await getCatalogSnapshot();
    expect(result.source).toBe("supabase");
    expect(result.performances).toHaveLength(1001);
    expect(result.performances.at(-1)?.id).toBe("last");
    expect(result.reviewQueue).toEqual([]);
    expect(ranges.performances).toHaveBeenNthCalledWith(2, 1000, 1999);
  });

  it("keeps an empty database empty", async () => {
    database({});
    const { getCatalogSnapshot } = await import("./catalog");
    expect(await getCatalogSnapshot()).toEqual({
      performances: [],
      works: [],
      reviewQueue: [],
      source: "supabase",
    });
  });

  it("reuses date formatters while preserving Korean performance dates", async () => {
    const OriginalFormatter = Intl.DateTimeFormat;
    const descriptor = Object.getOwnPropertyDescriptor(Intl, "DateTimeFormat")!;
    let formatterCount = 0;
    Object.defineProperty(Intl, "DateTimeFormat", {
      ...descriptor,
      value: class extends OriginalFormatter {
        constructor(...args: ConstructorParameters<typeof OriginalFormatter>) {
          super(...args);
          formatterCount += 1;
        }
      },
    });
    try {
      database({
        performances: [[performance("first"), performance("second")]],
      });
      const { getCatalogSnapshot } = await import("./catalog");
      const result = await getCatalogSnapshot();
      expect(
        result.performances.map(({ date, time }) => ({ date, time })),
      ).toEqual([
        { date: "2026-12-01", time: "19:00" },
        { date: "2026-12-01", time: "19:00" },
      ]);
      expect(formatterCount).toBeLessThanOrEqual(3);
    } finally {
      Object.defineProperty(Intl, "DateTimeFormat", descriptor);
    }
  });

  it("preserves unranked works and their source links past the API page boundary", async () => {
    const row = {
      slug: "wikidata-q11980",
      title: "Für Elise",
      title_ko: null,
      catalogue: "WoO 59",
      popularity_rank: null,
      composers: { id: "beethoven", name: "Beethoven" },
    };
    database({
      works: [
        Array.from({ length: 1000 }, (_, i) => ({ ...row, slug: `work-${i}` })),
        [row],
      ],
    });
    const { getCatalogSnapshot } = await import("./catalog");
    const result = await getCatalogSnapshot();
    expect(result.works).toHaveLength(1001);
    expect(result.works.at(-1)).toMatchObject({
      popularityRank: null,
      referenceUrl: "https://www.wikidata.org/wiki/Q11980",
    });
  });

  it("loads subsequent large-catalog pages with bounded concurrency", async () => {
    let active = 0;
    let maximum = 0;
    mocks.createSupabaseClient.mockReturnValue({
      from: (table: string) => {
        const query = {
          order: () => query,
          range: async (start: number) => {
            if (table !== "works") return { data: [], error: null };
            active += 1;
            maximum = Math.max(maximum, active);
            await new Promise((resolve) => setTimeout(resolve, 1));
            active -= 1;
            return {
              data:
                start < 3000
                  ? Array.from({ length: 1000 }, (_, i) => ({
                      slug: `w-${start + i}`,
                      title: "Work",
                    }))
                  : [],
              error: null,
            };
          },
        };
        return { select: () => query };
      },
    });
    const { getCatalogSnapshot } = await import("./catalog");
    expect((await getCatalogSnapshot()).works).toHaveLength(3000);
    expect(maximum).toBeGreaterThan(1);
    expect(maximum).toBeLessThanOrEqual(4);
  });

  it("excludes legacy demo performances and keeps closed distinct from sold out", async () => {
    database({
      performances: [
        [
          performance("perf-incheon-brahms"),
          { ...performance("PF123456"), status: "closed" },
        ],
      ],
    });
    const { getCatalogSnapshot } = await import("./catalog");
    const result = await getCatalogSnapshot();
    expect(result.performances.map((p) => p.id)).toEqual(["PF123456"]);
    expect(result.performances[0].status).toBe("closed");
  });

  it("does not publish a partial catalog or sample review queue when queries fail", async () => {
    database({ performances: [[performance("p")]] }, "works");
    const { getCatalogSnapshot } = await import("./catalog");
    expect(await getCatalogSnapshot()).toEqual({
      performances: [],
      works: [],
      reviewQueue: [],
      source: "unavailable",
    });
  });
});

describe("targeted detail queries", () => {
  afterEach(() => {
    vi.useRealTimers();
    mocks.configured.value = true;
    mocks.createSupabaseClient.mockReset();
    vi.resetModules();
  });

  function database(fail = false, observationProvider = "codex_vision") {
    const rows: Record<string, Record<string, unknown>[]> = {
      works: [
        {
          slug: "wikidata-q3565331",
          title: "Waldszenen",
          title_ko: "숲의 정경",
          catalogue: "Op. 82",
          composers: { id: "schumann", name: "Robert Schumann" },
          work_aliases: [{ alias: "Forest Scenes" }],
        },
        {
          slug: "component-wikidata-q3565331-3",
          title: "Einsame Blumen",
          title_ko: "고독한 꽃",
          composers: { id: "schumann", name: "Robert Schumann" },
        },
      ],
      performances: [
        {
          kopis_performance_id: "PF123456",
          title: "Recital",
          starts_at: "2099-12-01T10:00:00Z",
          status: "upcoming",
          program_items: [
            {
              display_title: "Einsame Blumen",
              position: 1,
              confidence: 1,
              source_type: "official",
              works: { slug: "component-wikidata-q3565331-3" },
            },
            {
              display_title: "Another work",
              position: 2,
              source_provider: observationProvider,
              confidence: 1,
              source_type: "official",
              works: { slug: "another" },
            },
          ],
        },
      ],
    };
    const filters: [string, string, unknown][] = [];
    const from = vi.fn((table: string) => {
      let filtered = rows[table] ?? [];
      const result = () => ({
        data: filtered,
        error: fail ? new Error("offline") : null,
      });
      const query = {
        select: vi.fn(() => query),
        order: vi.fn(() => query),
        range: vi.fn(async (start: number, end: number) => ({
          ...result(),
          data: filtered.slice(start, end + 1),
        })),
        eq: vi.fn((column: string, value: string) => {
          filters.push([table, column, value]);
          filtered = filtered.filter((row) => row[column] === value);
          return query;
        }),
        in: vi.fn((column: string, values: string[]) => {
          filters.push([table, column, values]);
          if (column === "slug")
            filtered = filtered.filter((row) =>
              values.includes(row.slug as string),
            );
          return query;
        }),
        maybeSingle: vi.fn(async () => ({
          ...result(),
          data: filtered[0] ?? null,
        })),
        then: (resolve: (value: unknown) => unknown) =>
          Promise.resolve(result()).then(resolve),
      };
      return query;
    });
    mocks.createSupabaseClient.mockReturnValue({ from });
    return { from, filters, rows };
  }

  it("reads only the requested performance, without loading the work catalog", async () => {
    const { from, filters } = database();
    const { getCatalogPerformanceById } = await import("./catalog");
    const result = await getCatalogPerformanceById("PF123456");
    expect(result.performance?.program).toHaveLength(2);
    expect(result.performance?.program[1].source).toMatchObject({
      confidence: null,
      label: "이미지 판독",
    });
    expect(from.mock.calls.map(([table]) => table)).toEqual(["performances"]);
    expect(filters).toContainEqual([
      "performances",
      "kopis_performance_id",
      "PF123456",
    ]);
  });

  it("labels verified Paddle evidence without inventing an accuracy percentage", async () => {
    database(false, "paddleocr");
    const { getCatalogPerformanceById } = await import("./catalog");
    const result = await getCatalogPerformanceById("PF123456");
    expect(result.performance?.program[1].source).toMatchObject({
      confidence: null,
      label: "OCR 근거 확인",
    });
  });

  it("reads a component and its related works, preserving parent names and all concert program items", async () => {
    const { filters } = database();
    const { getCatalogWorkBySlug } = await import("./catalog");
    const result = await getCatalogWorkBySlug("component-wikidata-q3565331-3");
    expect(result.work?.partOf?.[0]).toMatchObject({
      slug: "wikidata-q3565331",
      titleKo: "숲의 정경",
      position: 3,
      aliases: ["Forest Scenes"],
    });
    expect(result.performances[0].program).toHaveLength(2);
    expect(
      filters.some(
        ([table, column, value]) =>
          table === "works" &&
          column === "slug" &&
          (value as string[]).includes("component-wikidata-q3565331-3"),
      ),
    ).toBe(true);
    expect(filters).toContainEqual([
      "performances",
      "matched.works.slug",
      ["component-wikidata-q3565331-3"],
    ]);
  });

  it("distinguishes a missing detail from a database failure", async () => {
    database();
    const { getCatalogPerformanceById } = await import("./catalog");
    expect((await getCatalogPerformanceById("missing")).performance).toBeNull();
    database(true);
    await expect(getCatalogPerformanceById("PF123456")).rejects.toThrow();
  });

  it("splits work history from upcoming concerts without changing watchlist selections", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-23T15:30:00Z")); // October 24 in Seoul.
    const { rows } = database();
    const template = rows.performances[0];
    rows.performances = [
      { ...template, kopis_performance_id: "old", starts_at: "2024-11-24T07:00:00Z", status: "closed" },
      { ...template, kopis_performance_id: "yesterday", starts_at: "2026-10-23T10:00:00Z", status: "open" },
      { ...template, kopis_performance_id: "ongoing", starts_at: "2024-01-01T10:00:00Z", ends_on: "2026-10-24", status: "open" },
      { ...template, kopis_performance_id: "today", starts_at: "2026-10-23T15:00:00Z" },
      { ...template, kopis_performance_id: "tomorrow", starts_at: "2026-10-25T10:00:00Z" },
      { ...template, kopis_performance_id: "cancelled", starts_at: "2026-11-01T10:00:00Z", status: "closed" },
      { ...template, kopis_performance_id: "ended-series", starts_at: "2023-01-01T10:00:00Z", ends_on: "2026-10-22", status: "closed" },
    ];
    const { getCatalogWorkBySlug, getCatalogSelection } = await import("./catalog");
    const detail = await getCatalogWorkBySlug("component-wikidata-q3565331-3");
    expect(detail.performances.map((p) => p.id)).toEqual(["today", "tomorrow", "ongoing"]);
    expect(detail.pastPerformances.map((p) => p.id)).toEqual(["cancelled", "yesterday", "ended-series", "old"]);
    expect(detail.pastPerformances.at(-1)?.program).toHaveLength(2);
    expect(detail.work?.upcomingPerformanceIds).toEqual(["today", "tomorrow", "ongoing"]);
    const watchlist = await getCatalogSelection(["component-wikidata-q3565331-3"]);
    expect(watchlist.performances).toEqual(detail.performances);
    expect(watchlist).not.toHaveProperty("pastPerformances");
  });

  it("keeps linked history beyond the first API page without duplicating concerts", async () => {
    const { rows } = database();
    const template = rows.performances[0];
    rows.performances = Array.from({ length: 1001 }, (_, i) => ({
      ...template,
      kopis_performance_id: `old-${i}`,
      starts_at: "2024-11-24T07:00:00Z",
      status: "closed",
    }));
    const { getCatalogWorkBySlug } = await import("./catalog");
    const detail = await getCatalogWorkBySlug("component-wikidata-q3565331-3");
    expect(detail.pastPerformances).toHaveLength(1001);
    expect(new Set(detail.pastPerformances.map((p) => p.id)).size).toBe(1001);
    expect(detail.performances).toEqual([]);
  });

  it("distinguishes empty or missing work history from a failed database query", async () => {
    const { rows } = database();
    rows.performances = [];
    const { getCatalogWorkBySlug } = await import("./catalog");
    expect(await getCatalogWorkBySlug("component-wikidata-q3565331-3")).toMatchObject({
      performances: [], pastPerformances: [], work: { slug: "component-wikidata-q3565331-3" },
    });
    expect(await getCatalogWorkBySlug("missing")).toEqual({
      performances: [], pastPerformances: [], work: null,
    });
    database(true);
    await expect(getCatalogWorkBySlug("component-wikidata-q3565331-3")).rejects.toThrow();
  });
});
