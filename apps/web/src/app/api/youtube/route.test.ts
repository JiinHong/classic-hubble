import { works } from "@classic-hubble/shared";
import { afterEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ metadata: vi.fn(), catalog: vi.fn() }));
vi.mock("@/lib/youtube-server", () => ({
  createYouTubeHandler: () => mocks.metadata,
}));
vi.mock("@/lib/catalog", () => ({ getCatalogSnapshot: mocks.catalog }));
import { POST } from "./route";
const request = () =>
  new Request("https://example.com/api/youtube", { method: "POST" });
const video = {
  id: "AbCdEf123_-",
  title: "Beethoven Symphony No. 5 Op. 67",
  description: "",
  channelTitle: "Concert",
};
afterEach(() => vi.resetAllMocks());
describe("server-side YouTube matching", () => {
  it("returns matching candidates rather than the complete work database", async () => {
    mocks.metadata.mockResolvedValue(Response.json({ video }));
    mocks.catalog.mockResolvedValue({ works, source: "supabase" });
    const response = await POST(request());
    const body = await response.json();
    expect(body.result.entries[0].candidates[0].work.slug).toBe(
      "beethoven-symphony-5",
    );
    expect(body.result.entries[0].candidates[0].work.aliases).toEqual([]);
    expect(body.works).toBeUndefined();
    expect(response.headers.get("cache-control")).toBe("no-store");
  });
  it("does not load the catalog when video lookup fails", async () => {
    mocks.metadata.mockResolvedValue(
      Response.json({ error: "video_unavailable" }, { status: 404 }),
    );
    expect((await POST(request())).status).toBe(404);
    expect(mocks.catalog).not.toHaveBeenCalled();
  });
  it("distinguishes a catalog outage from a video with no known work", async () => {
    mocks.metadata.mockResolvedValue(Response.json({ video }));
    mocks.catalog.mockResolvedValue({ source: "unavailable" });
    expect((await POST(request())).status).toBe(503);
  });
});
