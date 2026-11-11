// @vitest-environment node
import { writeFileSync } from "node:fs";
import { expect, it, vi } from "vitest";
vi.mock("next/cache", () => ({ unstable_cache: (fn: unknown) => fn }));

it.skipIf(!process.env.CONCERT_PAGE_MEASURE)("measures one anonymous performance search without a catalog snapshot", async () => {
  const original = globalThis.fetch;
  const requests: { path: string; decodedBytes: number }[] = [];
  vi.stubGlobal("fetch", async (...args: Parameters<typeof fetch>) => {
    const response = await original(...args);
    const url = new URL(String(args[0]));
    if (url.hostname.endsWith(".supabase.co")) {
      expect(url.hostname).toBe("klnfamtwxwrelrjeguqb.supabase.co");
      requests.push({ path: url.pathname, decodedBytes: (await response.clone().arrayBuffer()).byteLength });
    }
    return response;
  });
  try {
    const { getPerformanceSearchPage } = await import("./performance-search");
    const query = "루트비히 판 베토벤";
    const start = performance.now();
    const result = await getPerformanceSearchPage(query);
    expect(requests.length).toBeGreaterThan(0);
    const measurement = { at: new Date().toISOString(), query, ms: Math.round(performance.now() - start),
      total: result.total, displayed: result.performances.map(p => p.id), requests,
      decodedDbBytes: requests.reduce((n, r) => n + r.decodedBytes, 0),
      clientBytes: Buffer.byteLength(JSON.stringify(result)) };
    writeFileSync(process.env.CONCERT_PAGE_MEASURE!, JSON.stringify(measurement, null, 2), { flag: "wx", mode: 0o600 });
  } finally { vi.unstubAllGlobals(); }
}, 60000);
