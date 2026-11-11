// @vitest-environment node
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import { getCatalogSnapshot, type CatalogSnapshot } from "./catalog";
import { searchCatalog } from "./catalog-search";
import { identifyYouTubeWorks } from "./youtube-matching";

// Preserve within-run page reuse: the legacy compressed-group fallback re-reads
// pages through Next's cache, not through the database a second time.
vi.mock("next/cache", () => ({ unstable_cache: (fn: (...args: unknown[]) => unknown) => {
  const values = new Map<string, Promise<unknown>>();
  return (...args: unknown[]) => {
    const key = JSON.stringify(args);
    if (!values.has(key)) values.set(key, Promise.resolve().then(() => fn(...args)).catch(error => { values.delete(key); throw error; }));
    return values.get(key);
  };
} }));

// Explicit opt-in only. The baseline is downloaded once and reused from local disk.
describe.skipIf(!process.env.TARGETED_CATALOG_SNAPSHOT)("targeted catalog live parity", () => {
  it("compares complete results and measures decoded DB bodies separately from HTTP client bytes", async () => {
    const path = process.env.TARGETED_CATALOG_SNAPSHOT!;
    const originalFetch = globalThis.fetch;
    const requests: { path: string; bytes: number; ms: number }[] = [];
    vi.stubGlobal("fetch", async (...args: Parameters<typeof fetch>) => {
      const start = performance.now();
      const response = await originalFetch(...args);
      if (String(args[0]).includes(".supabase.co/rest/")) {
        requests.push({ path: new URL(String(args[0])).pathname, bytes: (await response.clone().arrayBuffer()).byteLength, ms: performance.now() - start });
      }
      return response;
    });
    try {
      let snapshot: { at: string; loadMs: number; bytes: number; requests: number; dbRequests?: typeof requests; catalog: CatalogSnapshot };
      if (!existsSync(path)) {
        const start = performance.now();
        const catalog = await getCatalogSnapshot();
        expect(catalog.source).toBe("supabase");
        snapshot = { at: new Date().toISOString(), loadMs: performance.now() - start, bytes: requests.reduce((sum, r) => sum + r.bytes, 0), requests: requests.length, dbRequests: [...requests], catalog };
        writeFileSync(path, JSON.stringify(snapshot));
      } else snapshot = JSON.parse(readFileSync(path, "utf8"));
      console.info(JSON.stringify({ baseline: { at: snapshot.at, loadMs: snapshot.loadMs, bytes: snapshot.bytes, requests: snapshot.requests, catalog: { works: snapshot.catalog.works.length, performances: snapshot.catalog.performances.length } } }));
      if (process.env.TARGETED_CATALOG_COMPARE !== "1") return;
      const seoulDate = (date: Date) => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(date);
      expect(seoulDate(new Date()), "Use a same-Seoul-day baseline for current-date SQL functions").toBe(seoulDate(new Date(snapshot.at)));
      const { getPerformanceSearchPage } = await import("./performance-search");
      const { identifyYouTubeFromDatabase } = await import("./youtube-candidates");
      const reports: unknown[] = [];
      for (const [query, city, offset] of [
        ["", "전체", 0], ["", "서울", 24], ["베토벤", "전체", 0], ["운명", "전체", 0],
        ["라흐 피협 2번", "전체", 0], ["서울", "전체", 0], ["OCR 근거 확인", "전체", 0],
        ["%_", "전체", 0], ["definitely-not-a-concert", "전체", 0],
      ] as const) {
        const start = performance.now();
        // The legacy snapshot contains upcoming performances only.
        const expected = searchCatalog(snapshot.catalog, { query, city, offset, mode: "performances", period: "upcoming" });
        const oldComputeMs = performance.now() - start;
        requests.length = 0;
        const changedAt = performance.now();
        const actual = await getPerformanceSearchPage(query, city, offset, "upcoming");
        expect(actual, `performance ${query}/${city}/${offset}`).toMatchObject({
          performances: expected.performances, total: expected.total, hasMore: expected.hasMore, works: [],
        });
        reports.push({ kind: "performance", query, city, offset, count: actual.total, oldComputeMs, newMs: performance.now() - changedAt, bytes: requests.reduce((sum, r) => sum + r.bytes, 0), requests: [...requests] });
      }
      for (const video of [
        { title: "Beethoven Symphony No. 5 Op. 67", description: "" },
        { title: "베토벤 운명", description: "" },
        { title: "Frédéric Chopin Nocturne Op. 9 No. 2", description: "" },
        { title: "Schumann Waldszenen Op. 82: III. Einsame Blumen", description: "" },
        { title: "Waldszenen", description: "Composer: Robert Schumann\n00:00 III. Einsame Blumen" },
        { title: "Spring", description: "" },
        { title: "Beethoven Piano Concerto No. 2 in C minor Op. 18", description: "" },
        { title: "Unknown recording", description: "Subscribe https://example.com Beethoven" },
        { title: "Saint-Saëns The Swan", description: "" },
        { title: "Dvořák Symphony No. 9 Op. 95", description: "" },
        { title: "Bach The Swan", description: "" },
        { title: "Satie Gymnopédie No. 1", description: "" },
        { title: "Chopin Nocturne Op. 9 No. 2; Schumann Waldszenen Op. 82", description: "" },
        { title: "베토벤", description: "" },
      ]) {
        const start = performance.now();
        const expected = identifyYouTubeWorks(video, snapshot.catalog.works);
        const oldComputeMs = performance.now() - start;
        requests.length = 0;
        const changedAt = performance.now();
        const actual = await identifyYouTubeFromDatabase(video);
        expect(actual, video.title).toEqual(expected);
        reports.push({ kind: "youtube", video, count: actual.entries.length, oldComputeMs, newMs: performance.now() - changedAt, bytes: requests.reduce((sum, r) => sum + r.bytes, 0), requests: [...requests] });
      }
      writeFileSync(path + `.comparison-${Date.now()}.json`, JSON.stringify({ at: new Date().toISOString(), baseline: { loadMs: snapshot.loadMs, bytes: snapshot.bytes, requests: snapshot.requests, at: snapshot.at }, reports }, null, 2));
      console.info(JSON.stringify(reports.map(r => { const { requests: calls, ...summary } = r as { requests: unknown[] }; return { ...summary, requests: calls.length }; })));
    } finally { vi.unstubAllGlobals(); }
  }, 180000);
});
