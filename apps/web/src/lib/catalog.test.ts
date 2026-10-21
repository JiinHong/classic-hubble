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
