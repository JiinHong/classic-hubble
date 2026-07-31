import { existsSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  groupComposers,
  selectFeaturedComposers,
  toComposerDirectoryEntry,
} from "@/lib/composer-directory";

import koreanNames from "./composer-korean-names.json";
import koreanNameProvenance from "./composer-korean-name-provenance.json";
import composers from "./openopus-composers.json";

type KoreanNameProvenance = Record<
  string,
  {
    displayName: string;
    review: {
      note: string;
      status: "reviewed" | "sparse-ko-institutional-usage";
    };
    sources: Array<{
      publisher: string;
      title: string;
      url: string;
    }>;
  }
>;

describe("Open Opus composer snapshot", () => {
  it("contains a broad, composer-only, unique baseline", () => {
    expect(composers.length).toBeGreaterThanOrEqual(200);
    expect(new Set(composers.map((composer) => composer.name)).size).toBe(
      composers.length,
    );
    const periods = new Set(composers.map((composer) => composer.period));
    for (const expectedPeriod of [
      "Medieval",
      "Renaissance",
      "Baroque",
      "Classical",
      "Early Romantic",
      "Romantic",
      "Late Romantic",
      "20th Century",
      "Post-War",
      "21st Century",
    ]) {
      expect(periods.has(expectedPeriod)).toBe(true);
    }
    for (const composer of composers) {
      expect(Object.keys(composer).sort()).toEqual([
        "name",
        "nameKo",
        "period",
      ]);
    }

    const originalNames = composers.map((composer) => composer.name).toSorted();
    const localizedNames = Object.keys(koreanNames).toSorted();

    expect(localizedNames).toEqual(originalNames);
    expect(Object.values(koreanNames)).toHaveLength(composers.length);

    for (const label of Object.values(koreanNames)) {
      expect(label.trim()).toBe(label);
      expect(label).toMatch(/[가-힣]/);
    }
  });

  it("has four local portrait representatives for every named period", () => {
    const directory = composers.map((composer, index) =>
      toComposerDirectoryEntry({
        id: `openopus:${index}`,
        ...composer,
      }),
    );
    const featuredGroups = groupComposers(directory)
      .map((group) => ({
        composers: selectFeaturedComposers(group.composers),
        key: group.key,
      }))
      .filter((group) => group.composers.length > 0);

    expect(
      featuredGroups.map((group) => ({
        count: group.composers.length,
        key: group.key,
      })),
    ).toEqual([
      { count: 4, key: "medieval" },
      { count: 4, key: "renaissance" },
      { count: 4, key: "baroque" },
      { count: 4, key: "classical" },
      { count: 4, key: "romantic" },
      { count: 4, key: "twentieth" },
      { count: 4, key: "contemporary" },
    ]);

    for (const composer of featuredGroups.flatMap((group) => group.composers)) {
      expect(composer.portraitSrc).not.toBeNull();
      expect(
        existsSync(
          path.join(process.cwd(), "public", composer.portraitSrc!.slice(1)),
        ),
      ).toBe(true);
    }
  });

  it("documents review provenance for every Korean composer label", () => {
    const provenance =
      koreanNameProvenance as unknown as KoreanNameProvenance;
    const localizedNames = Object.keys(koreanNames).toSorted();
    const provenanceNames = Object.keys(provenance).toSorted();

    expect(provenanceNames).toEqual(localizedNames);

    for (const [name, label] of Object.entries(koreanNames)) {
      const entry = provenance[name];

      expect(entry.displayName).toBe(label);
      expect(entry.sources.length).toBeGreaterThanOrEqual(1);
      expect(entry.review.status).toMatch(
        /^(reviewed|sparse-ko-institutional-usage)$/,
      );

      if (entry.review.status === "reviewed") {
        expect(entry.sources.length).toBeGreaterThanOrEqual(2);
      } else {
        expect(entry.review.note.trim().length).toBeGreaterThan(0);
      }

      for (const source of entry.sources) {
        expect(source.publisher.trim()).toBe(source.publisher);
        expect(source.publisher.length).toBeGreaterThan(0);
        expect(source.title.trim()).toBe(source.title);
        expect(source.title.length).toBeGreaterThan(0);
        expect(() => new URL(source.url)).not.toThrow();
        expect(source.url).toMatch(/^https:\/\//);
      }
    }
  });
});
