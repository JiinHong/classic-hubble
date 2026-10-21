import { works } from "@classic-hubble/shared";
import { afterEach, describe, expect, it, vi } from "vitest";
const getCatalogSnapshot = vi.hoisted(() => vi.fn());
vi.mock("@/lib/catalog", () => ({ getCatalogSnapshot }));
import { GET } from "./route";
afterEach(() => getCatalogSnapshot.mockReset());
describe("public catalog search route", () => {
  it("rejects oversized queries and invalid offsets before loading data", async () => {
    for (const query of [
      "q=" + "x".repeat(201),
      "offset=-1",
      "offset=NaN",
      "mode=everything",
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
  });
  it("reports unavailability as an error, not an empty search", async () => {
    getCatalogSnapshot.mockResolvedValue({ source: "unavailable" });
    const response = await GET(
      new Request("https://example.com/api/catalog/search"),
    );
    expect(response.status).toBe(503);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(response.headers.has("Vercel-CDN-Cache-Control")).toBe(false);
  });
  it("returns only the requested public result page", async () => {
    getCatalogSnapshot.mockResolvedValue({
      source: "supabase",
      works,
      performances: [],
    });
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
      /^catalog;dur=\d+(\.\d+)?, search;dur=\d+(\.\d+)?$/,
    );
    expect((await response.json()).works[0].slug).toBe("beethoven-symphony-5");
  });
});
