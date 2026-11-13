import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { composerDiscoveryHref, composerIdentityKey, toComposerDirectoryEntry } from "@/lib/composer-directory";
import ComposerPage from "./page";

const { from } = vi.hoisted(() => ({ from: vi.fn() }));
vi.mock("next/cache", () => ({ unstable_cache: (fn: unknown) => fn }));
vi.mock("@/lib/supabase/client", () => ({
  isSupabaseConfigured: true,
  createSupabaseClient: () => ({ from }),
}));

beforeEach(() => from.mockReset());

describe("composer profile links from the directory", () => {
  it.each(["Léonin", "Guillaume de Machaut", "Pérotin"])(
    "opens the encoded directory link for %s even without linked works",
    async (name) => {
      const composer = toComposerDirectoryEntry({
        id: "openopus:" + composerIdentityKey(name), name, nameKo: null, period: "Medieval",
      });
      const segment = composerDiscoveryHref(composer).split("/").at(-1)!;
      const query = {
        select: vi.fn().mockReturnThis(), eq: vi.fn().mockReturnThis(),
        maybeSingle: vi.fn().mockResolvedValue({ data: null, error: null }),
      };
      from.mockReturnValue(query);
      render(await ComposerPage({ params: Promise.resolve({ id: segment }), searchParams: Promise.resolve({}) }));
      expect(screen.getByRole("heading", { name: composer.nameKo })).toBeTruthy();
      expect(screen.getByText("아직 연결된 작품이 없습니다.")).toBeTruthy();
      expect(query.eq).toHaveBeenCalledWith("name", name);
    },
  );

  it.each(["openopus%3Anot%20in%20the%20catalog", "%ZZ", "openopus%253Aleonin"])(
    "keeps unrecognized or malformed IDs as not found: %s", async (id) => {
      await expect(ComposerPage({ params: Promise.resolve({ id }), searchParams: Promise.resolve({}) }))
        .rejects.toThrow(/404/);
      expect(from).not.toHaveBeenCalled();
    },
  );
});
