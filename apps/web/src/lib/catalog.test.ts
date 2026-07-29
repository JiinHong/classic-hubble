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
