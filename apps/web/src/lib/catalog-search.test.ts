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
  it("returns linked history newest first without mixing it into upcoming concerts", () => {
    expect(searchCatalog(catalog, {}).performances).toEqual([]);
    const base = performances.find(p => p.program.some(i => i.workSlug === "beethoven-symphony-5"))!;
    const data = { works, performances: ["2021-03-01", "2027-01-01", "2026-05-01"].map((date, i) =>
      ({ ...base, id: String(i), title: "정기연주회", date, endDate: undefined })) };
    const search = { query: "루트비히 판 베토벤", mode: "performances" as const };
    const all = searchCatalog(data, search);
    expect(all.performances.map(p => p.id)).toEqual(["1", "2", "0"]);
    expect(all.periodCounts).toEqual({ upcoming: 1, past: 2 });
    expect(searchCatalog(data, { ...search, query: "운명", period: "past" }).performances.map(p => p.id)).toEqual(["2", "0"]);
    expect(searchCatalog(data, { ...search, period: "upcoming" }).total).toBe(1);
  });
});
