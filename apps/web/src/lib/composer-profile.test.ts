import { beforeEach, describe, expect, it, vi } from "vitest";
import { getComposerProfile } from "./composer-profile";
const { from } = vi.hoisted(() => ({ from: vi.fn() }));
vi.mock("next/cache", () => ({ unstable_cache: (fn: unknown) => fn }));
vi.mock("./supabase/client", () => ({ isSupabaseConfigured: true, createSupabaseClient: () => ({ from }) }));
const id = "6a3a69b3-185b-5d27-bbba-e50a7c23aaed";
const composer = { id, name: "Frédéric Chopin", name_ko: "프레데리크 쇼팽", period: "Romantic" };
beforeEach(() => { from.mockReset(); });
describe("composer profile", () => {
  it("builds facets only from that composer, including works past the first database page", async () => {
    const personQuery = { select: vi.fn().mockReturnThis(), eq: vi.fn().mockReturnThis(), maybeSingle: vi.fn().mockResolvedValue({ data: composer }) };
    const workQuery = { select: vi.fn().mockReturnThis(), eq: vi.fn().mockReturnThis(), order: vi.fn().mockReturnThis(),
      range: vi.fn().mockImplementation(async (start: number, end: number) => ({ data: start === 0
        ? Array.from({length: end + 1}, (_, i) => ({slug: "n"+i, title: "Nocturne "+i, title_ko: null, catalogue:null}))
        : [{ slug: "a", title: "Scherzo", title_ko: "스케르초", catalogue: null }] })) };
    from.mockImplementation(t => t === "composers" ? personQuery : workQuery);
    const profile = await getComposerProfile(id, 1, "scherzo");
    expect(personQuery.eq).toHaveBeenCalledWith("id", id);
    expect(workQuery.eq).toHaveBeenCalledWith("composer_id", id);
    expect(workQuery.range.mock.calls).toEqual([[0,499],[500,999]]);
    expect(profile).toMatchObject({ composer: { id }, count: 501, selectedCount: 1, works: [{ slug: "a" }] });
  });
  it("rejects made-up profiles without contacting the database", async () => {
    expect(await getComposerProfile("openopus:not a real composer", 1)).toBeNull();
    expect(from).not.toHaveBeenCalled();
  });
  it("does not ask for an out-of-range page after exactly 500 works", async () => {
    const query = { select: vi.fn().mockReturnThis(), eq: vi.fn().mockReturnThis(), order: vi.fn().mockReturnThis(),
      maybeSingle: vi.fn().mockResolvedValue({data: composer}), range: vi.fn()
        .mockResolvedValueOnce({ count: 500, data: Array.from({length:500}, (_,i)=>({ slug: "w"+i, title: "Study "+i, title_ko:null, catalogue:null })) })
        .mockResolvedValue({ data:null, error:{code:"PGRST103"} }) };
    from.mockReturnValue(query);
    expect((await getComposerProfile(id,1))?.count).toBe(500);
    expect(query.range).toHaveBeenCalledTimes(1);
  });
  it("does not present database errors as empty works", async () => {
    const query = { select: vi.fn().mockReturnThis(), eq: vi.fn().mockReturnThis(),
      maybeSingle: vi.fn().mockResolvedValue({ data: null, error: { code: "503" } }) };
    from.mockReturnValue(query);
    await expect(getComposerProfile(id, 1)).rejects.toThrow();
  });
});
