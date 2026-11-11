import { works } from "@classic-hubble/shared";
import { afterEach, describe, expect, it, vi } from "vitest";
const { getCatalogSnapshot, getWorkSearchPage } = vi.hoisted(() => ({ getCatalogSnapshot: vi.fn(), getWorkSearchPage: vi.fn() }));
const { getPerformanceSearchPage } = vi.hoisted(() => ({ getPerformanceSearchPage: vi.fn() }));
vi.mock("@/lib/performance-search", () => ({ getPerformanceSearchPage }));
vi.mock("@/lib/catalog", () => ({ getCatalogSnapshot }));
vi.mock("@/lib/work-search", () => ({ getWorkSearchPage }));
import { searchCatalog } from "@/lib/catalog-search";
import { GET } from "./route";
afterEach(() => { getCatalogSnapshot.mockReset(); getWorkSearchPage.mockReset(); getPerformanceSearchPage.mockReset(); });
describe("public catalog search route", () => {
  it("rejects oversized queries and invalid offsets before loading data", async () => {
    for (const query of [
      "q=" + "x".repeat(201),
      "offset=-1",
      "offset=NaN",
      "mode=everything",
      "period=tomorrow",
    ]) {
      expect(
        (
          await GET(
            new Request(`https://example.com/api/catalog/search?${query}`),
          )
        ).status,
      ).toBe(400);
    }
    expect(getCatalogSnapshot).not.toHaveBeenCalled();
    expect(getWorkSearchPage).not.toHaveBeenCalled();
  });
  it("reports unavailability as an error, not an empty search", async () => {
    getWorkSearchPage.mockRejectedValue(new Error("unavailable"));
    const response = await GET(
      new Request("https://example.com/api/catalog/search"),
    );
    expect(response.status).toBe(503);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(response.headers.has("Vercel-CDN-Cache-Control")).toBe(false);
  });
  it("returns only the requested public result page", async () => {
    getWorkSearchPage.mockResolvedValue(searchCatalog({ works, performances: [] }, { query: "운명" }));
    const response = await GET(
      new Request(
        "https://example.com/api/catalog/search?q=" +
          encodeURIComponent("운명"),
      ),
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(response.headers.get("Vercel-CDN-Cache-Control")).toBe(
      "public, s-maxage=60, stale-while-revalidate=300",
    );
    expect(response.headers.get("Server-Timing")).toMatch(
      /^targeted;dur=\d+(\.\d+)?$/,
    );
    expect((await response.json()).works[0].slug).toBe("beethoven-symphony-5");
    expect(getCatalogSnapshot).not.toHaveBeenCalled();
    expect(getWorkSearchPage).toHaveBeenCalledWith("운명", 0);
  });
  it("retains the separate performance search path", async () => {
    getPerformanceSearchPage.mockResolvedValue({ works: [], performances: [], total: 0, hasMore: false });
    const response = await GET(new Request("https://example.com/api/catalog/search?mode=performances&q=운명&city=서울&offset=24"));
    expect(response.status).toBe(200);
    expect(getPerformanceSearchPage).toHaveBeenCalledWith("운명", "서울", 24, "all");
    expect(getCatalogSnapshot).not.toHaveBeenCalled();
    expect(getWorkSearchPage).not.toHaveBeenCalled();
  });
  it("reports performance candidate errors without a full-catalog fallback", async () => {
    getPerformanceSearchPage.mockRejectedValue(new Error("offline"));
    expect((await GET(new Request("https://example.com/api/catalog/search?mode=performances"))).status).toBe(503);
    expect(getCatalogSnapshot).not.toHaveBeenCalled();
  });
});
