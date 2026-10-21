import { performances, works } from "@classic-hubble/shared";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { searchCatalog } from "./catalog-search";

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-01"));
});
afterEach(() => vi.useRealTimers());
const catalog = { works, performances };

describe("bounded catalog search", () => {
  it("sends 24 works at a time while searching the complete catalog", () => {
    const many = Array.from({ length: 1000 }, (_, i) => ({
      ...works[0],
      slug: `w${i}`,
      titleKo: `Piece ${i}`,
      aliases: i === 999 ? ["rare nickname"] : [],
    }));
    expect(searchCatalog({ works: many, performances: [] }, {})).toMatchObject({
      total: 1000,
      hasMore: true,
    });
    expect(
      searchCatalog({ works: many, performances: [] }, {}).works,
    ).toHaveLength(24);
    expect(
      searchCatalog({ works: many, performances: [] }, { offset: 24 }).works[0]
        .slug,
    ).toBe("w24");
    expect(
      searchCatalog(
        { works: many, performances: [] },
        { query: "rare nickname" },
      ).works.map((w) => w.slug),
    ).toEqual(["w999"]);
  });
  it("preserves composer and alias matching for performances", () => {
    const result = searchCatalog(catalog, {
      query: "세르게이 라흐마니노프",
      mode: "performances",
    });
    expect(result.total).toBe(2);
    expect(
      searchCatalog(catalog, {
        query: "세르게이 라흐마니노프",
        mode: "performances",
        city: "없는지역",
      }).total,
    ).toBe(0);
  });
  it("keeps component labels but omits server-only alias dictionaries from cards", () => {
    const part = {
      ...works[0],
      aliases: ["secret-to-render"],
      partOf: [
        {
          slug: "parent",
          title: "Collection",
          titleKo: "모음곡",
          catalogue: "Op. 1",
          position: 3,
          aliases: ["collection alias"],
        },
      ],
    };
    const result = searchCatalog({ works: [part], performances: [] }, {});
    expect(result.works[0].partOf?.[0]).toMatchObject({
      titleKo: "모음곡",
      position: 3,
    });
    expect(JSON.stringify(result)).not.toContain("secret-to-render");
    expect(JSON.stringify(result)).not.toContain("collection alias");
  });
  it("does not send the other result mode or past performances", () => {
    expect(searchCatalog(catalog, {}).performances).toEqual([]);
    const result = searchCatalog(
      {
        works,
        performances: performances.map((p) => ({
          ...p,
          date: "2020-01-01",
          endDate: undefined,
        })),
      },
      { mode: "performances" },
    );
    expect(result).toMatchObject({ works: [], performances: [], total: 0 });
  });
});
