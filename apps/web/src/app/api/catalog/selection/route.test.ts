import { works, performances } from "@classic-hubble/shared";
import { afterEach, expect, it, vi } from "vitest";
const catalog = vi.hoisted(() => vi.fn());
vi.mock("@/lib/catalog", () => ({ getCatalogSnapshot: catalog }));
import { GET } from "./route";
afterEach(() => {
  vi.resetAllMocks();
  vi.useRealTimers();
});
it("returns only explicitly selected public works and their upcoming performances", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-01"));
  catalog.mockResolvedValue({ works, performances, source: "supabase" });
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
  expect(catalog).not.toHaveBeenCalled();
});
it("does not confuse an unavailable catalog with an empty library", async () => {
  catalog.mockResolvedValue({ source: "unavailable" });
  expect(
    (await GET(new Request("https://example.com/api/catalog/selection?slug=w")))
      .status,
  ).toBe(503);
});
