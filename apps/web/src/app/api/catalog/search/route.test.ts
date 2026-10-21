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
    expect(
      (await GET(new Request("https://example.com/api/catalog/search"))).status,
    ).toBe(503);
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
    expect((await response.json()).works[0].slug).toBe("beethoven-symphony-5");
  });
});
