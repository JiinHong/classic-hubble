import { afterEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ rpc: vi.fn(), client: vi.fn() }));
vi.mock("./supabase/client", () => ({ createSupabaseClient: mocks.client }));
vi.mock("next/cache", () => ({ unstable_cache: (fn: unknown) => fn }));
import { getWorkSuggestions } from "./work-suggestions";
afterEach(() => vi.clearAllMocks());
describe("lightweight work suggestions", () => {
  it("skips empty and punctuation-only input", async () => {
    expect(await getWorkSuggestions("   ")).toEqual([]);
    expect(await getWorkSuggestions("---")).toEqual([]);
    expect(mocks.client).not.toHaveBeenCalled();
  });
  it("makes one bounded RPC and returns only the suggestion contract", async () => {
    mocks.client.mockReturnValue({ rpc: mocks.rpc });
    mocks.rpc.mockResolvedValue({ data: [{ slug: "work-1", title: "피아노 협주곡 2번", composer: "라흐마니노프" }], error: null });
    expect(await getWorkSuggestions("라흐 피협 2번")).toEqual([{ slug: "work-1", title: "피아노 협주곡 2번", composer: "라흐마니노프" }]);
    expect(mocks.rpc).toHaveBeenCalledExactlyOnceWith("suggest_works", { search_term: "라흐 피협 2번" });
  });
  it("does not turn DB failure into no suggestions", async () => {
    mocks.client.mockReturnValue({ rpc: mocks.rpc });
    mocks.rpc.mockResolvedValue({ data: null, error: { message: "offline" } });
    await expect(getWorkSuggestions("운명")).rejects.toThrow();
  });
});
