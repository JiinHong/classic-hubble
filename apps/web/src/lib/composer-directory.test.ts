import { describe, expect, it } from "vitest";

import {
  composerDiscoveryHref,
  composerIdentityKey,
  filterAndSortComposers,
  groupComposers,
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

describe("composer directory rules", () => {
  it("normalizes period and derives core status", () => {
    expect(bach.period).toBe("baroque");
    expect(bach.isCore).toBe(true);
    expect(debussy.period).toBe("twentieth");
    expect(unknown.period).toBe("other");
    expect(unknown.nameKo).toBe("Unknown Composer");
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
    ).toMatchObject({ isCore: true, nameKo: "요제프 하이든" });
    expect(
      toComposerDirectoryEntry({
        id: "schnittke",
        name: "Alfred Schnittke",
        nameKo: null,
        period: "Post-War",
      }).period,
    ).toBe("contemporary");
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

  it("builds an encoded composer discovery link", () => {
    expect(composerDiscoveryHref(bach)).toBe(
      `/?composer=${encodeURIComponent("요한 제바스티안 바흐")}`,
    );
    expect(composerIdentityKey("Frédéric Chopin")).toBe("frederic chopin");
  });
});
