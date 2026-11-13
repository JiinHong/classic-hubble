import { beforeEach, describe, expect, it, vi } from "vitest";
import { getComposerProfile } from "./composer-profile";
const { from } = vi.hoisted(() => ({ from: vi.fn() }));
vi.mock("next/cache", () => ({ unstable_cache: (fn: unknown) => fn }));
vi.mock("./supabase/client", () => ({ isSupabaseConfigured: true, createSupabaseClient: () => ({ from }) }));
const id = "6a3a69b3-185b-5d27-bbba-e50a7c23aaed";
const composer = { id, name: "Frédéric Chopin", name_ko: "프레데리크 쇼팽", period: "Romantic" };
beforeEach(() => { from.mockReset(); });
describe("composer profile", () => {
  it("reads one composer and only a bounded page of that composer's works", async () => {
    const personQuery = { select: vi.fn().mockReturnThis(), eq: vi.fn().mockReturnThis(), maybeSingle: vi.fn().mockResolvedValue({ data: composer }) };
    const workQuery = { select: vi.fn().mockReturnThis(), eq: vi.fn().mockReturnThis(), order: vi.fn().mockReturnThis(),
      range: vi.fn().mockResolvedValue({ count: 50, data: [{ slug: "a", title: "Nocturne", title_ko: "녹턴", catalogue: null }] }) };
    from.mockImplementation(t => t === "composers" ? personQuery : workQuery);
    const profile = await getComposerProfile(id, 2);
    expect(personQuery.eq).toHaveBeenCalledWith("id", id);
    expect(workQuery.eq).toHaveBeenCalledWith("composer_id", id);
    expect(workQuery.order.mock.calls.map(([column]) => column)).toEqual(["popularity_rank", "title_ko", "title", "slug"]);
    expect(workQuery.range).toHaveBeenCalledWith(24, 47);
    expect(profile).toMatchObject({ composer: { id }, count: 50, works: [{ slug: "a" }] });
  });
  it("rejects made-up profiles without contacting the database", async () => {
    expect(await getComposerProfile("openopus:not a real composer", 1)).toBeNull();
    expect(from).not.toHaveBeenCalled();
  });
  it("does not present database errors as empty works", async () => {
    const query = { select: vi.fn().mockReturnThis(), eq: vi.fn().mockReturnThis(),
      maybeSingle: vi.fn().mockResolvedValue({ data: null, error: { code: "503" } }) };
    from.mockReturnValue(query);
    await expect(getComposerProfile(id, 1)).rejects.toThrow();
  });
});
