import { works, performances } from "@classic-hubble/shared";
import { beforeEach, expect, it, vi } from "vitest";
const get = vi.hoisted(() => vi.fn());
vi.mock("@/lib/catalog", () => ({ getCatalogWorkBySlug: get }));
import { GET } from "./route";
beforeEach(() => { get.mockReset(); });
it("uses the exact selected work slug and paginates upcoming concerts only", async () => {
  get.mockResolvedValue({ work: works[0], performances: Array.from({ length: 30 }, (_, i) => ({ ...performances[0], id: `p${i}` })), pastPerformances: [performances[1]] });
  const r = await GET(new Request("https://example.com?work=exact-work&offset=24"));
  const body = await r.json();
  expect(get).toHaveBeenCalledExactlyOnceWith("exact-work");
  expect(body.performances).toHaveLength(6); expect(body.total).toBe(30); expect(body.hasMore).toBe(false);
});
it("validates identifiers and distinguishes missing work from an outage", async () => {
  expect((await GET(new Request("https://example.com?work=../bad"))).status).toBe(400);
  expect(get).not.toHaveBeenCalled();
  get.mockResolvedValue({ work: null });
  expect((await GET(new Request("https://example.com?work=missing"))).status).toBe(404);
  get.mockRejectedValue(new Error("offline"));
  expect((await GET(new Request("https://example.com?work=missing"))).status).toBe(503);
});
