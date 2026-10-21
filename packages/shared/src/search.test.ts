import { describe, expect, it } from "vitest";
import { findWorksByQuery, getPerformanceById, getWorkBySlug } from "./index";

describe("Classic Hubble shared search helpers", () => {
  it("matches Korean shorthand aliases to canonical works", () => {
    const results = findWorksByQuery("라흐 피협 2번");

    expect(results[0]?.slug).toBe("rachmaninoff-piano-concerto-2");
    expect(results[0]?.composer.nameKo).toBe("세르게이 라흐마니노프");
  });

  it("finds a work detail page by slug", () => {
    const work = getWorkBySlug("beethoven-symphony-5");

    expect(work?.aliases).toContain("운명");
    expect(work?.upcomingPerformanceIds.length).toBeGreaterThan(0);
  });

  it("finds a performance with normalized program items", () => {
    const performance = getPerformanceById("perf-lotte-rach-2");

    expect(performance?.program[0]?.workSlug).toBe(
      "rachmaninoff-piano-concerto-2",
    );
    expect(performance?.program[0]?.source.confidence).toBeGreaterThan(0.8);
  });
});
import { findWorksByQueryInList, works } from "./index";

describe("reference catalog search", () => {
  it("matches Korean aliases regardless of spacing or Hangul decomposition", () => {
    const work = {
      ...works[0],
      title: "Piano Concerto No. 3",
      titleKo: "피아노 협주곡 3번",
      aliases: ["라흐 피협 3번"],
    };
    for (const query of [
      "라흐피협3번", "라흐피협 3번", "라흐 피협 3번".normalize("NFD"),
    ]) {
      expect(findWorksByQueryInList([work], query)).toEqual([work]);
    }
  });

  it("keeps multiple works for an ambiguous Korean nickname", () => {
    const sonata = { ...works[0], slug: "beethoven-pathetique", aliases: ["비창"] };
    const symphony = { ...works[1], slug: "tchaikovsky-pathetique", aliases: ["비창"] };
    expect(findWorksByQueryInList([sonata, symphony], "비창")).toHaveLength(2);
  });

  it("uses the composer to rank an ambiguous nickname instead of input order", () => {
    const sonata = {
      ...works[0], slug: "beethoven-pathetique", aliases: ["비창"],
      titleKo: "피아노 소나타 8번 '비창'",
      composer: { ...works[0].composer, nameKo: "베토벤" },
    };
    const symphony = {
      ...works[0], slug: "tchaikovsky-pathetique", aliases: ["비창"],
      titleKo: "교향곡 6번 '비창'",
      composer: { ...works[0].composer, nameKo: "차이콥스키" },
    };
    expect(findWorksByQueryInList([symphony, sonata], "베토벤 비창")[0]).toEqual(sonata);
    expect(findWorksByQueryInList([sonata, symphony], "차이콥스키 비창")[0]).toEqual(symphony);
  });

  it("does not hide a matching work with no popularity measurement", () => {
    const work = { ...works[0], popularityRank: 999 };
    expect(findWorksByQueryInList([work], work.title)).toEqual([work]);
  });

  it("does not treat missing metadata as a match for an unrelated query", () => {
    const work = { ...works[0], catalogue: "", aliases: [], popularityRank: 1 };
    expect(findWorksByQueryInList([work], "zzzzzzzz")).toEqual([]);
  });
});
