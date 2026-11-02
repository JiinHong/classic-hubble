import { afterEach, describe, expect, it, vi } from "vitest";
import { findWorksByQueryInList, works } from "@classic-hubble/shared";
import { mapWorks } from "./catalog";
import { getHomeOverview, getWorkSearchPage } from "./work-search";

const mocks = vi.hoisted(() => ({ client: vi.fn() }));
vi.mock("./supabase/client", () => ({ createSupabaseClient: () => mocks.client() }));
vi.mock("next/cache", () => ({ unstable_cache: (fn: unknown) => fn }));
afterEach(() => vi.clearAllMocks());

function database() {
  const rows = works.map((work, i) => ({
    id: `id-${i}`, slug: work.slug, title: work.title, title_ko: work.titleKo,
    catalogue: work.catalogue, popularity_rank: work.popularityRank, instrumentation: work.instrumentation,
    composers: { id: work.composer.id, name: work.composer.name, name_ko: work.composer.nameKo, period: work.composer.period },
    work_aliases: work.aliases.map(alias => ({ alias })),
  }));
  const state = { rows, candidates: rows, links: [] as { work_id: string; performance_id: string }[], fail: "" };
  const reads: { table: string; filter?: [string, unknown[]]; range?: number[] }[] = [];
  const builder = (table: string, data: unknown[], count = data.length) => {
    const read: typeof reads[number] = { table };
    reads.push(read);
    const result = () => ({ data, count, error: state.fail === table ? { message: "offline" } : null });
    const query = {
      select: () => query, order: () => query,
      in: (column: string, values: unknown[]) => {
        read.filter = [column, values];
        data = data.filter(row => values.includes((row as Record<string, unknown>)[column]));
        return query;
      },
      range: (start: number, end: number) => { read.range = [start, end]; data = data.slice(start, end + 1); return query; },
      then: (resolve: (result: unknown) => unknown) => Promise.resolve(result()).then(resolve),
    };
    return query;
  };
  const rpc = vi.fn((name: string) => builder(name,
    name === "search_work_candidates" ? state.candidates : name === "work_upcoming_links" ? state.links :
      [{ work_count: 20000, upcoming_count: 300, confirmed_count: 99, performance_ids: [] }],
  ));
  mocks.client.mockReturnValue({ from: (table: string) => builder(table, state.rows), rpc });
  return { state, reads, rpc };
}

describe("targeted work search", () => {
  it("browses only 24 works with an exact total, not the full catalog", async () => {
    const { state, reads } = database();
    state.rows = Array.from({ length: 1500 }, (_, i) => ({ ...state.rows[0], id: `id-${i}`, slug: `w-${i}` }));
    const result = await getWorkSearchPage("", 24);
    expect(result).toMatchObject({ total: 1500, hasMore: true, performances: [] });
    expect(result.works).toHaveLength(24);
    expect(result.works[0].slug).toBe("w-24");
    expect(reads.find(read => read.table === "works")?.range).toEqual([24, 47]);
    expect(reads.some(read => read.table === "performances")).toBe(false);
  });

  it.each(["라흐 피협 2번", "브바협", "운명", "베토벤 교향곡 5번", "라흐피협2번", "unknown", "비창"])(
    "retains existing ranking for %s and loads links only for displayed works", async query => {
      const { state, rpc } = database();
      const expected = findWorksByQueryInList(mapWorks(state.rows, []), query);
      const result = await getWorkSearchPage(query);
      expect(result.works.map(work => work.slug)).toEqual(expected.map(work => work.slug));
      expect(result.total).toBe(expected.length);
      expect(rpc).toHaveBeenCalledWith("search_work_candidates", { search_term: expect.any(String) });
      if (expected.length) expect(rpc).toHaveBeenCalledWith("work_upcoming_links", {
        work_ids: expected.map(work => state.rows.find(row => row.slug === work.slug)!.id),
      });
    },
  );

  it("keeps candidates after the 1000-row API boundary", async () => {
    const { state, reads } = database();
    state.candidates = Array.from({ length: 1001 }, (_, i) => ({ ...state.rows[0], id: `id-${i}`, slug: `w-${i}`, title: "Needle", title_ko: "Needle" }));
    const result = await getWorkSearchPage("needle", 984);
    expect(result.total).toBe(1001);
    expect(result.works).toHaveLength(17);
    expect(reads.filter(read => read.table === "search_work_candidates").map(read => read.range)).toEqual([[0, 999], [1000, 1999]]);
  });

  it("retrieves a child through its parent's title and preserves parent context", async () => {
    const { state } = database();
    const parent = { ...state.rows[0], id: "parent", slug: "wikidata-q3565331", title: "Waldszenen", title_ko: "숲의 정경", catalogue: "Op. 82", composers: { id: "s", name: "Robert Schumann", name_ko: "로베르트 슈만", period: "Romantic" }, work_aliases: [] };
    const child = { ...parent, id: "child", slug: "component-wikidata-q3565331-3", title: "Einsame Blumen", title_ko: "고독한 꽃", catalogue: "" };
    state.rows = [parent, child]; state.candidates = [parent];
    const result = await getWorkSearchPage("슈만 숲의 정경 3번");
    expect(result.works.map(work => work.slug)).toEqual([child.slug]);
    expect(result.works[0].partOf?.[0].slug).toBe(parent.slug);
  });

  it("finds synthetic component positions even when no own title matches", async () => {
    const { state } = database();
    const parent = { ...state.rows[0], id: "parent", slug: "wikidata-q3565331", title: "Waldszenen", title_ko: "숲의 정경", catalogue: "Op. 82", work_aliases: [] };
    state.rows = [parent, { ...parent, id: "child", slug: "component-wikidata-q3565331-3", title: "Einsame Blumen", title_ko: "고독한 꽃", catalogue: "" }];
    state.candidates = [];
    expect((await getWorkSearchPage("3번")).works.map(work => work.slug)).toEqual(["component-wikidata-q3565331-3"]);
  });

  it("does not query for punctuation-only search and does not cache errors as empty results", async () => {
    const { state, rpc } = database();
    expect((await getWorkSearchPage("---")).total).toBe(0);
    expect(rpc).not.toHaveBeenCalled();
    state.fail = "search_work_candidates";
    await expect(getWorkSearchPage("운명")).rejects.toThrow();
    state.fail = "";
    expect((await getWorkSearchPage("운명")).works.length).toBeGreaterThan(0);
  });

  it("deduplicates public upcoming links and propagates link query errors", async () => {
    const { state } = database();
    state.links = [{ work_id: state.rows[0].id, performance_id: "PF1" }, { work_id: state.rows[0].id, performance_id: "PF1" }];
    expect((await getWorkSearchPage()).works[0].upcomingPerformanceIds).toEqual(["PF1"]);
    state.fail = "work_upcoming_links";
    await expect(getWorkSearchPage()).rejects.toThrow();
  });

  it("loads aggregate home counts without loading the full catalog", async () => {
    const { reads } = database();
    expect(await getHomeOverview()).toEqual({ workCount: 20000, upcomingCount: 300, confirmedCount: 99, performances: [] });
    expect(reads.map(read => read.table)).toEqual(["home_catalog_overview"]);
  });

  it("retains more than 1000 upcoming links and does not silently truncate their count", async () => {
    const { state } = database();
    state.links = Array.from({ length: 1001 }, (_, i) => ({ work_id: state.rows[0].id, performance_id: `PF${i}` }));
    expect((await getWorkSearchPage()).works[0].upcomingPerformanceIds).toHaveLength(1001);
  });

  it("does not fall back to a catalog scan for an unknown title", async () => {
    const { state, reads } = database();
    state.candidates = [];
    expect((await getWorkSearchPage("nothingmatches")).total).toBe(0);
    expect(reads.map(read => read.table)).toEqual(["search_work_candidates"]);
  });
});
