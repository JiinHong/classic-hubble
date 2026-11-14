// @vitest-environment node
import { describe, expect, it, vi } from "vitest";
import { normalizeWorkSearchText } from "@classic-hubble/shared";
import { createSupabaseClient } from "./supabase/client";
import { getHomeOverview, getWorkSearchPage } from "./work-search";
import { getWorkSuggestions } from "./work-suggestions";

vi.mock("next/cache", () => ({ unstable_cache: (fn: unknown) => fn }));

// Opt-in read-only checks against the configured database; never run by default CI.
describe.skipIf(process.env.WORK_SEARCH_INTEGRATION !== "1")("work search SQL contract", () => {
  it("keeps SQL retrieval normalization identical to the shared matcher", async () => {
    const db = createSupabaseClient();
    for (const value of [
      "라흐 피협 2번", "라흐피협제2번", "바협5번", "피소 제3곡", "현악4중주 제14번",
      "현사2번", "라흐피협", "Op. 82 No. 3 (숲의 정경)-“꽃”", "K. 4330",
      "협주곡".normalize("NFD"), "100%_literal\\path", "---", "피협x", "피협2번끝",
    ]) {
      const result = await db.rpc("work_search_normalize", { value });
      expect(result.error).toBeNull();
      expect(result.data, value).toBe(normalizeWorkSearchText(value));
    }
  }, 30000);

  it.each([
    ["라흐 피협 2번", "rachmaninoff-piano-concerto-2", 4],
    ["베토벤 교향곡 5번", "beethoven-symphony-5", 3],
    ["슈만 숲의 정경 3번", "component-wikidata-q3565331-3", 1],
  ])("retains measured results for %s", async (query, slug, total) => {
    const started = performance.now();
    const result = await getWorkSearchPage(query);
    expect(result.total).toBe(total);
    expect(result.works.map(work => work.slug)).toContain(slug);
    console.info(JSON.stringify({ query, total: result.total, elapsedMs: performance.now() - started, slugs: result.works.map(work => work.slug) }));
  }, 30000);

  it("supports joined composer names and treats wildcard characters literally", async () => {
    const result = await getWorkSearchPage("모차르트터키풍");
    expect(result.total).toBeGreaterThan(0);
    expect(result.works.every(work => work.composer.nameKo.includes("모차르트"))).toBe(true);
    expect((await getWorkSearchPage("%_")).total).toBe(0);
  }, 30000);

  it.each([
    ["달빛", "wikidata-q29117946"],
    ["드뷔시 달빛", "wikidata-q29117946"],
    ["드뷔시달빛", "wikidata-q29117946"],
    ["Clair de lune", "wikidata-q29117946"],
    ["포레 달빛", "wikidata-q730599"],
  ])("finds the intended Clair de lune in results and suggestions: %s", async (query, slug) => {
    const result = await getWorkSearchPage(query);
    const suggestions = await getWorkSuggestions(query);
    expect(result.works[0]?.slug).toBe(slug);
    expect(suggestions[0]?.slug).toBe(slug);
    if (query === "달빛") {
      expect(result.works[0].partOf).toContainEqual(expect.objectContaining({
        slug: "wikidata-q1367599", position: 3,
      }));
      for (const rows of [result.works, suggestions]) {
        expect(rows.map(row => row.slug)).toContain("wikidata-q730599");
      }
    }
  }, 30000);

  it("serves anonymous overview and a bounded first page", async () => {
    const overview = await getHomeOverview();
    const page = await getWorkSearchPage();
    expect(page.works).toHaveLength(24);
    expect(page.total).toBe(overview.workCount);
    expect(overview.performances).toHaveLength(4);
    expect(overview.upcomingCount).toBeGreaterThanOrEqual(overview.confirmedCount);
  }, 30000);
});
