import { works, type Work } from "@classic-hubble/shared";
import { describe, expect, it } from "vitest";
import { identifyYouTubeWorks } from "./youtube-matching";

const beethoven = works.find(w => w.slug === "beethoven-symphony-5")!;
const schumann: Work["composer"] = { id: "schumann", name: "Robert Schumann", nameKo: "로베르트 슈만", period: "Romantic" };
const parent: Work = { ...beethoven, slug: "forest", composer: schumann, title: "Waldszenen", titleKo: "숲의 정경", catalogue: "Op. 82", aliases: ["숲 속의 정경"], upcomingPerformanceIds: ["parent-only"] };
const flower: Work = { ...parent, slug: "flower", title: "Einsame Blumen", titleKo: "고독한 꽃", catalogue: "Op. 82 No. 3", aliases: ["고독한 꽃"], partOf: [{ ...parent, position: 3 }], upcomingPerformanceIds: [] };
const catalog = [...works, parent, flower];
const identify = (title: string, description = "", items = catalog) => identifyYouTubeWorks({ title, description }, items);
const slugs = (result: ReturnType<typeof identify>) => result.entries.flatMap(e => e.candidates.map(c => c.work.slug));

describe("metadata work candidates", () => {
  it("uses composer and exact catalogue with extra recording text", () => {
    const result = identify("Beethoven: Symphony No. 5 in C minor, Op. 67 | Live 4K");
    expect(slugs(result)).toEqual([beethoven.slug]);
    expect(result.entries[0].candidates[0].reason).toBe("composer_catalogue");
  });
  it("finds Korean nicknames with composer context", () => {
    expect(slugs(identify("베토벤 운명 교향곡 실황"))).toEqual([beethoven.slug]);
  });
  it("finds a distinctive title without guessing a composer", () => {
    expect(slugs(identify("고독한 꽃"))).toEqual([flower.slug]);
  });
  it("does not confuse catalogue prefixes", () => {
    expect(slugs(identify("Beethoven Symphony No. 5 Op. 670"))).toEqual([]);
  });
  it("does not match a different known composer", () => {
    expect(slugs(identify("Schumann: Symphony No. 5 in C minor Op. 67"))).toEqual([]);
  });
  it("rejects conflicting work numbers and keys", () => {
    expect(slugs(identify("Beethoven Symphony No. 6 Op. 67"))).toEqual([]);
    expect(slugs(identify("Beethoven Symphony No. 5 in D major Op. 67"))).toEqual([]);
  });
  it("does not merge a component with the whole work or inherit concerts", () => {
    const result = identify("R. Schumann: Waldszenen, Op. 82 No. 3 - Einsame Blumen");
    expect(slugs(result)).toEqual([flower.slug]);
    expect(result.entries[0].candidates[0].work.upcomingPerformanceIds).toEqual([]);
  });
  it("recognizes collection plus numbered component without the piece title", () => {
    expect(slugs(identify("슈만 숲의 정경 3번"))).toEqual([flower.slug]);
  });
  it("lists distinct timestamped pieces and retains timestamps as evidence", () => {
    const result = identify("Piano recital", "0:00 Beethoven Symphony No. 5 Op. 67\n12:20 Schumann Einsame Blumen Op. 82 No. 3");
    expect(slugs(result)).toEqual([beethoven.slug, flower.slug]);
    expect(result.entries[1].timestamp).toBe("12:20");
    expect(result.entries[1].text).toContain("Einsame Blumen");
  });
  it("uses an explicit composer credit for a generic work title", () => {
    expect(slugs(identify("Symphony No. 5 in C minor, Op. 67", "Composer: Ludwig van Beethoven"))).toEqual([beethoven.slug]);
  });
  it("does not treat unrelated description prose or URL as a track", () => {
    expect(slugs(identify("Interview", "My favorite work is Beethoven Symphony No. 5 Op. 67 and we discuss it.\nhttps://example.com/Beethoven/Op.67"))).toEqual([]);
  });
  it("keeps ambiguous candidates rather than silently selecting a popular one", () => {
    const candidates = Array.from({length: 5}, (_, i) => ({...beethoven, slug: `work-${i}`, catalogue: "", title: "Adagio", titleKo: "아다지오", aliases: ["Adagio"]}));
    const result = identify("Beethoven Adagio", "", candidates);
    expect(result.entries[0].ambiguous).toBe(true);
    expect(result.entries[0].candidates).toHaveLength(3);
  });
  it("does not infer works from only a composer or a generic tempo", () => {
    expect(slugs(identify("Beethoven best music"))).toEqual([]);
    expect(slugs(identify("Adagio", "", [{...beethoven, title: "Adagio", aliases: []}]))).toEqual([]);
  });
  it("deduplicates the same title repeated in the description", () => {
    expect(slugs(identify("Beethoven Op. 67", "Beethoven Op. 67"))).toEqual([beethoven.slug]);
  });
  it("ignores aliases that contain only the composer's name", () => {
    const noise = {...beethoven, slug: "noise", catalogue: "", title: "Germany", titleKo: "Germany", aliases: ["BEETHOVEN"]};
    expect(slugs(identify("Beethoven: Symphony No. 5 / Harnoncourt", "", [...catalog, noise]))).toEqual([beethoven.slug]);
  });
  it("constrains numbered tempo lines to children of the identified collection", () => {
    const second = {...flower, slug:"andante", title:"Andante con moto", titleKo:"Andante con moto", catalogue:"", aliases:[], partOf:[{...parent,position:2}]};
    const unrelated = {...second,slug:"unrelated",partOf:[]};
    const result = identify("Schumann Waldszenen Op. 82", "II. Andante con moto 07:25", [...catalog,second,unrelated]);
    expect(slugs(result)).toEqual([parent.slug, second.slug]);
  });
  it("does not identify unrelated generic movements without collection context", () => {
    const movement = {...flower, title:"Allegro", titleKo:"Allegro", aliases:[], catalogue:""};
    expect(slugs(identify("Schumann recital", "I. Allegro 00:15", [parent,movement]))).toEqual([]);
  });
});
