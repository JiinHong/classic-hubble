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
  it("expands observed genre shorthand without a per-work nickname entry", () => {
    const work = {
      ...works[0],
      title: "Piano Concerto No. 21",
      titleKo: "피아노 협주곡 21번 C장조",
      aliases: [],
      composer: { ...works[0].composer, nameKo: "볼프강 아마데우스 모차르트" },
    };
    const other = {
      ...work,
      slug: "other",
      title: "Piano Concerto No. 2",
      titleKo: "피아노 협주곡 2번",
    };
    for (const query of [
      "모차르트 피협 21번", "모차르트피협21번", "모차르트 피협21",
    ]) {
      expect(findWorksByQueryInList([other, work], query)).toEqual([work]);
    }
  });

  it("supports sonata and string-quartet shorthand across numbered works", () => {
    const sonata = {
      ...works[0],
      slug: "sonata",
      title: "Piano Sonata No. 32",
      titleKo: "피아노 소나타 32번",
      aliases: [],
      composer: { ...works[0].composer, nameKo: "베토벤" },
    };
    const quartet = {
      ...sonata,
      slug: "quartet",
      title: "String Quartet No. 12",
      titleKo: "현악 사중주 12번",
    };
    expect(findWorksByQueryInList([quartet, sonata], "베토벤피소32번")[0]).toEqual(sonata);
    expect(findWorksByQueryInList([sonata, quartet], "베토벤 현사12번")[0]).toEqual(quartet);
    expect(findWorksByQueryInList([sonata, quartet], "베토벤 현악4중주 제12번")[0]).toEqual(quartet);
  });

  it("does not give exact-number rank to a different ordinal", () => {
    const work = {
      ...works[0],
      titleKo: "교향곡 4번",
      title: "Symphony No. 4",
      aliases: [],
      composer: { ...works[0].composer, nameKo: "하이든" },
    };
    const other = {
      ...work, slug: "14", titleKo: "교향곡 14번", title: "Symphony No. 14",
    };
    expect(findWorksByQueryInList([other, work], "하이든 교향곡 4번")).toEqual([work]);
  });

  it("matches whole catalogue numbers instead of numeric prefixes", () => {
    const rondo = {
      ...works[0], slug: "rondo", title: "Rondo in C minor, Op. 1",
      titleKo: "론도 다단조", catalogue: "Op. 1", aliases: [],
      composer: { ...works[0].composer, name: "Frédéric Chopin", nameKo: "쇼팽" },
    };
    const variations = {
      ...rondo, slug: "variations", title: "Variations brillantes, Op. 12",
      titleKo: "론도 주제에 의한 화려한 변주곡", catalogue: "Op. 12",
    };
    expect(findWorksByQueryInList([variations, rondo], "쇼팽 론도 Op 1")).toEqual([rondo]);
    const sonata = { ...rondo, slug: "sonata", title: "Sonata K433", titleKo: "소나타", catalogue: "K433" };
    const other = { ...sonata, slug: "other", title: "Sonata K4330", catalogue: "K4330" };
    expect(findWorksByQueryInList([other, sonata], "소나타 K 433")).toEqual([sonata]);
  });

  it("ranks an explicit catalogue subnumber ahead of a collection with a shared alias", () => {
    const piece = {
      ...works[0], slug: "nocturne-17", title: "Nocturne No. 17 in B major, Op. 62 No. 1",
      titleKo: "야상곡 17번", catalogue: "Op. 62 No. 1", aliases: [],
      composer: { ...works[0].composer, name: "Frédéric Chopin", nameKo: "쇼팽" },
    };
    const collection = {
      ...piece, slug: "nocturnes-62", title: "Nocturnes, Op. 62", titleKo: "녹턴",
      catalogue: "Op. 62", aliases: ["Nocturne in B major, Op. 62, No. 1"],
    };
    expect(findWorksByQueryInList([collection, piece], "Chopin Nocturne Op 62 No 1")[0]).toEqual(piece);
  });

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

  it("distinguishes shared Korean titles with a composer and unspaced title token", () => {
    const schumann = {
      ...works[0], slug: "waldszenen", title: "Waldszenen", titleKo: "숲의 정경",
      catalogue: "Op. 82", aliases: [], popularityRank: null,
      composer: { ...works[0].composer, name: "Robert Schumann", nameKo: "로베르트 슈만" },
    };
    const macdowell = {
      ...schumann, slug: "woodland-sketches", title: "Woodland Sketches", catalogue: "Op. 51",
      composer: { ...schumann.composer, name: "Edward MacDowell", nameKo: "에드워드 맥도웰" },
    };
    const unrelated = { ...schumann, slug: "novelletten", title: "Novelletten", titleKo: "Novelletten" };
    const catalog = [unrelated, macdowell, schumann];
    expect(findWorksByQueryInList(catalog, "슈만 숲의정경")).toEqual([schumann]);
    expect(findWorksByQueryInList(catalog, "맥도웰 숲의정경")).toEqual([macdowell]);
    expect(findWorksByQueryInList(catalog, "숲의정경")).toEqual([macdowell, schumann]);
  });

  it("does not treat missing metadata as a match for an unrelated query", () => {
    const work = { ...works[0], catalogue: "", aliases: [], popularityRank: 1 };
    expect(findWorksByQueryInList([work], "zzzzzzzz")).toEqual([]);
  });
});
