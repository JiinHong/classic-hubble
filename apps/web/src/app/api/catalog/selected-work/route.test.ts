import { works, performances } from "@classic-hubble/shared";
import { beforeEach, expect, it, vi } from "vitest";
const get = vi.hoisted(() => vi.fn());
vi.mock("@/lib/performance-search", () => ({ getSelectedConcertPage: get }));
import { GET } from "./route";
beforeEach(() => { get.mockReset(); });
it("paginates selected work history by its exact slug, region and period", async () => {
  get.mockResolvedValue({ works: [works[0]], performances: [performances[1]], total: 25, hasMore: false });
  const r = await GET(new Request("https://example.com?work=exact-work&city=인천&period=past&offset=24"));
  const body = await r.json();
  expect(get).toHaveBeenCalledExactlyOnceWith("exact-work", "인천", 24, "past");
  expect(body.performances).toEqual([performances[1]]); expect(body.total).toBe(25); expect(body.hasMore).toBe(false);
});
it("validates identifiers and distinguishes missing work from an outage", async () => {
  expect((await GET(new Request("https://example.com?work=../bad"))).status).toBe(400);
  expect(get).not.toHaveBeenCalled();
  get.mockResolvedValue(null);
  expect((await GET(new Request("https://example.com?work=missing"))).status).toBe(404);
  get.mockRejectedValue(new Error("offline"));
  expect((await GET(new Request("https://example.com?work=missing"))).status).toBe(503);
});
