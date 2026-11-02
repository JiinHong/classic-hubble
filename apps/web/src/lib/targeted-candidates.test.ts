import { afterEach, describe, expect, it, vi } from "vitest";
import { works } from "@classic-hubble/shared";
import { mapWorks, type PerformanceRow } from "./catalog";
import { identifyYouTubeWorks } from "./youtube-matching";
import { attachWorkComponents } from "./work-components";
import workComponents from "@/data/work-components.json";
import { identifyYouTubeFromDatabase } from "./youtube-candidates";
import { getPerformanceSearchPage } from "./performance-search";

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
  const state = { candidates: rows, performances: [] as (PerformanceRow & { id: string })[], links: [] as { work_id: string; performance_id: string }[], fail: "" };
  const reads: { table: string; range?: number[] }[] = [];
  const builder = (table: string, data: unknown[]) => {
    const read: typeof reads[number] = { table }; reads.push(read);
    const query = {
      select: () => query, order: () => query,
      in: (column: string, values: unknown[]) => { data = data.filter(row => values.includes((row as Record<string, unknown>)[column])); return query; },
      range: (start: number, end: number) => { read.range = [start, end]; data = data.slice(start, end + 1); return query; },
      then: (resolve: (r: unknown) => unknown) => Promise.resolve({ data, error: state.fail === table ? { message: "offline" } : null }).then(resolve),
    }; return query;
  };
  const rpc = vi.fn((name: string) => builder(name, name === "search_performance_candidates" ? state.performances : name === "youtube_upcoming_links" ? state.links : state.candidates));
  const from = vi.fn((table: string) => builder(table, table === "performances" ? state.performances : []));
  mocks.client.mockReturnValue({ rpc, from });
  return { state, reads, rpc, from };
}

describe("targeted candidate services", () => {
  it("retains YouTube decisions and fills links only for final candidates", async () => {
    const { state, rpc, from } = database();
    const video = { title: "Beethoven Symphony No. 5 Op. 67", description: "" };
    const expected = identifyYouTubeWorks(video, attachWorkComponents(mapWorks(state.candidates, []), workComponents));
    const selected = expected.entries[0].candidates[0].work;
    const id = state.candidates.find(row => row.slug === selected.slug)!.id;
    state.links = [{ work_id: id, performance_id: "PF-later-id-earlier-date" }, { work_id: id, performance_id: "PF-A" }, { work_id: id, performance_id: "PF-A" }];
    selected.upcomingPerformanceIds = ["PF-later-id-earlier-date", "PF-A"];
    expect(await identifyYouTubeFromDatabase(video)).toEqual(expected);
    expect(rpc).toHaveBeenCalledWith("youtube_work_candidates", { video_text: video.title + "\n" });
    expect(rpc).toHaveBeenCalledWith("youtube_upcoming_links", { work_ids: [id] });
    expect(from).not.toHaveBeenCalledWith("performances");
  });

  it("keeps all ambiguous candidates before the matcher's top-three limit and pages past 1000", async () => {
    const { state, reads } = database();
    state.candidates = Array.from({ length: 1001 }, (_, i) => ({ ...state.candidates[0], id: `id-${i}`, slug: `work-${i}`, title: "Distinctive Spring", title_ko: "Distinctive Spring", catalogue: "", work_aliases: [] }));
    const video = { title: "Distinctive Spring", description: "" };
    const result = await identifyYouTubeFromDatabase(video);
    expect(result).toEqual(identifyYouTubeWorks(video, attachWorkComponents(mapWorks(state.candidates, []), workComponents)));
    expect(result.entries[0].ambiguous).toBe(true);
    expect(reads.filter(r => r.table === "youtube_work_candidates").map(r => r.range)).toEqual([[0, 999], [1000, 1999]]);
  });

  it("does not confuse an outage with an unmatched video or download all performances", async () => {
    const { state, rpc, from } = database();
    state.candidates = [];
    expect(await identifyYouTubeFromDatabase({ title: "Unknown", description: "" })).toEqual({ entries: [] });
    expect(rpc).not.toHaveBeenCalledWith("youtube_upcoming_links", expect.anything());
    state.fail = "youtube_work_candidates";
    await expect(identifyYouTubeFromDatabase({ title: "Unknown", description: "" })).rejects.toThrow();
    expect(from).not.toHaveBeenCalled();
  });

  it("passes every matched work ID to performance retrieval and keeps TS filtering", async () => {
    const { state, rpc } = database();
    state.candidates = Array.from({ length: 30 }, (_, i) => ({ ...state.candidates[0], id: `id-${i}`, slug: `w-${i}`, title: "Needle", title_ko: "Needle", work_aliases: [] }));
    expect(await getPerformanceSearchPage("Needle", "서울", 24)).toEqual({ works: [], performances: [], total: 0, hasMore: false });
    expect(rpc).toHaveBeenCalledWith("search_performance_candidates", { search_term: "needle", city_name: "서울", matched_work_ids: state.candidates.map(row => row.id) });
  });

  it("does not fetch works for empty performance browsing; propagates candidate failures", async () => {
    const { state, rpc, from } = database();
    await getPerformanceSearchPage("", "전체");
    expect(rpc).toHaveBeenCalledExactlyOnceWith("search_performance_candidates", { search_term: "", city_name: "전체", matched_work_ids: [] });
    expect(from).not.toHaveBeenCalled();
    state.fail = "search_performance_candidates";
    await expect(getPerformanceSearchPage("", "전체")).rejects.toThrow();
  });

  it("loads full performance details only for the displayed page", async () => {
    const { state, from } = database();
    state.performances = Array.from({ length: 25 }, (_, i) => ({
      id: `internal-${i}`, kopis_performance_id: `PF${i}`, title: `Concert ${i}`,
      starts_at: "2099-01-01T10:00:00Z", ends_on: null, status: "upcoming", artists: [],
      venues: { name: "Hall", city: "서울" }, program_items: [], booking_url: `https://example.com/${i}`,
      poster_url: "https://example.com/poster.jpg", price_range: null, program_image_urls: [],
      program_source_url: null, program_status: "unknown", source_label: "Official",
    }));
    const result = await getPerformanceSearchPage("", "전체", 24);
    expect(result.total).toBe(25);
    expect(result.performances).toHaveLength(1);
    expect(result.performances[0]).toMatchObject({ id: "PF24", bookingUrl: "https://example.com/24" });
    expect(from).toHaveBeenCalledExactlyOnceWith("performances");
    state.fail = "performances";
    await expect(getPerformanceSearchPage("", "전체", 24)).rejects.toThrow();
  });
});
