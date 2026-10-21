import { works, performances } from "@classic-hubble/shared";
import { afterEach, expect, it, vi } from "vitest";
const catalog = vi.hoisted(() => vi.fn());
const selection = vi.hoisted(() => vi.fn());
vi.mock("@/lib/catalog", () => ({
  getCatalogSnapshot: catalog,
  getCatalogSelection: selection,
}));
import { GET } from "./route";
afterEach(() => {
  vi.resetAllMocks();
  vi.useRealTimers();
});
it("returns only explicitly selected public works and their upcoming performances", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-01"));
  catalog.mockResolvedValue({ works, performances, source: "supabase" });
  selection.mockResolvedValue({
    works: [works[0]],
    performances: performances.slice(0, 2),
  });
  const response = await GET(
    new Request(
      "https://example.com/api/catalog/selection?slug=rachmaninoff-piano-concerto-2",
    ),
  );
  const body = await response.json();
  expect(body.works.map((work: { slug: string }) => work.slug)).toEqual([
    "rachmaninoff-piano-concerto-2",
  ]);
  expect(body.performances).toHaveLength(2);
  expect(selection).toHaveBeenCalledWith([works[0].slug]);
  expect(catalog).not.toHaveBeenCalled();
});
it("rejects oversized selections without querying the database", async () => {
  expect(
    (
      await GET(
        new Request(
          "https://example.com/api/catalog/selection?" +
            Array(101).fill("slug=w").join("&"),
        ),
      )
    ).status,
  ).toBe(400);
  expect(selection).not.toHaveBeenCalled();
  expect(catalog).not.toHaveBeenCalled();
});
it("rejects invalid slugs without querying the database", async () => {
  const response = await GET(
    new Request("https://example.com/api/catalog/selection?slug=%3Cinvalid%3E"),
  );
  expect(response.status).toBe(400);
  expect(selection).not.toHaveBeenCalled();
});
it("does not query an empty selection", async () => {
  const response = await GET(new Request("https://example.com/api/catalog/selection"));
  expect(await response.json()).toEqual({ works: [], performances: [] });
  expect(selection).not.toHaveBeenCalled();
});
it("deduplicates selected works before querying", async () => {
  selection.mockResolvedValue({ works: [], performances: [] });
  await GET(
    new Request("https://example.com/api/catalog/selection?slug=w&slug=w"),
  );
  expect(selection).toHaveBeenCalledWith(["w"]);
});
it("does not confuse an unavailable catalog with an empty library", async () => {
  catalog.mockResolvedValue({ source: "unavailable" });
  selection.mockRejectedValue(new Error("offline"));
  expect(
    (await GET(new Request("https://example.com/api/catalog/selection?slug=w")))
      .status,
  ).toBe(503);
});
