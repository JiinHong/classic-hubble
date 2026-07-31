import { describe, expect, it } from "vitest";

import {
  composerDiscoveryHref,
  composerIdentityKey,
  filterAndSortComposers,
  groupComposers,
  selectFeaturedComposers,
  toComposerDirectoryEntry,
} from "./composer-directory";

const bach = toComposerDirectoryEntry({
  id: "bach",
  name: "Johann Sebastian Bach",
  nameKo: "요한 제바스티안 바흐",
  period: "Baroque",
});
const debussy = toComposerDirectoryEntry({
  id: "debussy",
  name: "Claude Debussy",
  nameKo: "클로드 드뷔시",
  period: "20th Century",
});
const unknown = toComposerDirectoryEntry({
  id: "unknown",
  name: "Unknown Composer",
  nameKo: null,
  period: null,
});
const machaut = toComposerDirectoryEntry({
  id: "machaut",
  name: "Guillaume de Machaut",
  nameKo: null,
  period: "Medieval",
});

describe("composer directory rules", () => {
  it("normalizes periods and derives featured presentation metadata", () => {
    expect(bach.period).toBe("baroque");
    expect(bach.featuredRank).toBe(1);
    expect(bach.portraitSrc).toBe(
      "/composer-portraits/johann-sebastian-bach.jpg",
    );
    expect(debussy.period).toBe("twentieth");
    expect(unknown.period).toBe("other");
    expect(unknown.featuredRank).toBeNull();
    expect(unknown.portraitSrc).toBeNull();
    expect(unknown.nameKo).toBe("Unknown Composer");
    expect(machaut).toMatchObject({
      featuredRank: 1,
      nameKo: "기욤 드 마쇼",
      portraitSrc: "/composer-portraits/guillaume-de-machaut.jpg",
    });
    expect(
      toComposerDirectoryEntry({
        id: "adams",
        name: "John Adams",
        nameKo: null,
        period: "21st Century",
      }).period,
    ).toBe("contemporary");
    expect(
      toComposerDirectoryEntry({
        id: "haydn",
        name: "Franz Joseph Haydn",
        nameKo: null,
        period: "Classical",
      }),
    ).toMatchObject({ featuredRank: 2, nameKo: "요제프 하이든" });
    expect(
      toComposerDirectoryEntry({
        id: "schnittke",
        name: "Alfred Schnittke",
        nameKo: null,
        period: "Post-War",
      }).period,
    ).toBe("contemporary");
  });

  it("uses the reviewed Korean dictionary when the source label is empty", () => {
    expect(
      toComposerDirectoryEntry({
        id: "copland",
        name: "Aaron Copland",
        nameKo: null,
        period: "20th Century",
      }).nameKo,
    ).toBe("에런 코플런드");
  });

  it("keeps an explicit source label ahead of the reviewed dictionary", () => {
    expect(
      toComposerDirectoryEntry({
        id: "copland",
        name: "Aaron Copland",
        nameKo: "애런 코플랜드",
        period: "20th Century",
      }).nameKo,
    ).toBe("애런 코플랜드");
  });

  it("searches Korean and original-language names", () => {
    const entries = [bach, debussy];

    expect(
      filterAndSortComposers(entries, {
        period: "all",
        query: "바흐",
        sort: "ko",
      }).map((entry) => entry.id),
    ).toEqual(["bach"]);
    expect(
      filterAndSortComposers(entries, {
        period: "all",
        query: "debussy",
        sort: "ko",
      }).map((entry) => entry.id),
    ).toEqual(["debussy"]);
  });

  it("filters periods and supports Korean and Latin sorting", () => {
    const entries = [debussy, bach];

    expect(
      filterAndSortComposers(entries, {
        period: "baroque",
        query: "",
        sort: "ko",
      }).map((entry) => entry.id),
    ).toEqual(["bach"]);
    expect(
      filterAndSortComposers(entries, {
        period: "all",
        query: "",
        sort: "latin",
      }).map((entry) => entry.id),
    ).toEqual(["debussy", "bach"]);
  });

  it("keeps period groups in musical chronology", () => {
    expect(groupComposers([unknown, debussy, bach]).map((group) => group.key)).toEqual([
      "baroque",
      "twentieth",
      "other",
    ]);
  });

  it("selects at most four featured composers in editorial order", () => {
    const candidates = [
      { ...bach, id: "fifth", featuredRank: 5, name: "Five" },
      { ...bach, id: "third", featuredRank: 3, name: "Three" },
      { ...bach, id: "first", featuredRank: 1, name: "One" },
      { ...bach, id: "fourth", featuredRank: 4, name: "Four" },
      { ...bach, id: "second", featuredRank: 2, name: "Two" },
      unknown,
    ];

    expect(selectFeaturedComposers(candidates).map((entry) => entry.id)).toEqual([
      "first",
      "second",
      "third",
      "fourth",
    ]);
  });

  it("keeps four romantic representatives when Beethoven is curated as classical", () => {
    const entries = [
      {
        ...toComposerDirectoryEntry({
          id: "beethoven",
          name: "Ludwig van Beethoven",
          nameKo: null,
          period: "Classical",
        }),
      },
      toComposerDirectoryEntry({
        id: "chopin",
        name: "Frédéric Chopin",
        nameKo: null,
        period: "Romantic",
      }),
      toComposerDirectoryEntry({
        id: "tchaikovsky",
        name: "Pyotr Ilyich Tchaikovsky",
        nameKo: null,
        period: "Romantic",
      }),
      toComposerDirectoryEntry({
        id: "brahms",
        name: "Johannes Brahms",
        nameKo: null,
        period: "Romantic",
      }),
      toComposerDirectoryEntry({
        id: "schubert",
        name: "Franz Schubert",
        nameKo: null,
        period: "Early Romantic",
      }),
    ];
    const romanticGroup = groupComposers(entries).find(
      (group) => group.key === "romantic",
    );

    expect(
      selectFeaturedComposers(romanticGroup?.composers ?? []).map(
        (entry) => entry.name,
      ),
    ).toEqual([
      "Frédéric Chopin",
      "Pyotr Ilyich Tchaikovsky",
      "Johannes Brahms",
      "Franz Schubert",
    ]);
  });

  it("builds an encoded composer discovery link", () => {
    expect(composerDiscoveryHref(bach)).toBe(
      `/?composer=${encodeURIComponent("요한 제바스티안 바흐")}`,
    );
    expect(composerIdentityKey("Frédéric Chopin")).toBe("frederic chopin");
  });
});
