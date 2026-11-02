import { beforeEach, expect, it, vi } from "vitest";
const get = vi.hoisted(() => vi.fn());
vi.mock("@/lib/work-suggestions", () => ({ getWorkSuggestions: get }));
import { GET } from "./route";
beforeEach(() => { get.mockReset(); });
it("validates input and returns only the suggestion response", async () => {
  expect((await GET(new Request(`https://example.com?q=${"a".repeat(201)}`))).status).toBe(400);
  expect(get).not.toHaveBeenCalled();
  get.mockResolvedValue([{ slug: "a", title: "A", composer: "B" }]);
  expect(await (await GET(new Request("https://example.com?q=A"))).json()).toEqual({ suggestions: [{ slug: "a", title: "A", composer: "B" }] });
});
it("does not disguise unavailable suggestions as empty", async () => {
  get.mockRejectedValue(new Error("offline"));
  expect((await GET(new Request("https://example.com?q=A"))).status).toBe(503);
});
