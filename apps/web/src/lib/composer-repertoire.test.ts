import { describe, expect, it } from "vitest";
import { repertoire, classify, type WorkRow } from "./composer-repertoire";

const work = (slug: string, title: string, ko: string | null = null): WorkRow =>
  ({ slug, title, title_ko: ko, catalogue: null });

describe("composer repertoire", () => {
  it.each([
    ["Étude Op. 10", "etude"], ["24 Préludes", "prelude"], ["Scherzo No. 4", "scherzo"],
    ["Fantaisie-impromptu", "impromptu"], ["Ballade No. 3", "ballade"],
    ["Concerto for Piano and Orchestra no. 1", "piano-concerto"],
    ["Concerto for flute and harp", "concerto"], ["Violin Sonata in A", "violin-sonata"],
    ["Flute Concerto No. 2", "flute-concerto"], ["Trio Sonata in G", "trio-sonata"],
    ["Sinfonia concertante", "concertante"], ["Sinfonia No. 1, BWV 787", "invention"],
    ["Cantabile in B-flat major", "cantabile"], ["Polka française", "polka"],
    ["Variations on a theme from Mozart's opera Don Giovanni", "variation"],
    ["Overture to The Magic Flute", "overture"], ["Symphonic poem", "symphonic-poem"],
    ["String Quartet No. 11", "string-quartet"], ["Piano Quartet No. 2", "piano-quartet"],
    ["Prelude and Fugue in C", "prelude-fugue"], ["Music for a summer night", "other"],
  ])("classifies %s", (title, expected) => expect(classify(work("sample", title))).toBe(expected));
  it("uses a Korean title or an exact source identity without guessing from unrelated names", () => {
    expect(classify(work("song", "Untitled", "가곡집"))).toBe("song");
    expect(classify(work("wikidata-q471821", "Uninformative title"))).toBe("opera");
    expect(classify(work("mozart-die-zauberflote-k620", "Die Zauberflöte"))).toBe("opera");
    expect(classify(work("wikidata-q201873", "Le nozze di Figaro"))).toBe("opera");
    expect(classify(work("puccini-tosca", "Tosca"))).toBe("opera");
    expect(classify(work("verdi-aida", "Aida"))).toBe("opera");
    expect(classify(work("wikidata-q2401650", "Celeste Aida"))).not.toBe("opera");
  });
  it("keeps verified parts under parents and counts categories before pagination", () => {
    const works = [work("p", "Piano Sonata No. 2"), work("c", "Scherzo"), work("a", "Scherzo No. 2"),
      work("b", "Scherzo No. 10"), work("g", "Allegro"), work("l", "Étude")];
    const edges = [{parent_slug:"p",child_slug:"c",position:2},{parent_slug:"c",child_slug:"g",position:1},
      {parent_slug:"absent",child_slug:"l",position:1}];
    const all = repertoire(works, edges, undefined, 1, 1);
    expect(all.count).toBe(4);
    expect(all.componentCount).toBe(2);
    expect(all.facets.find(f => f.id === "scherzo")?.count).toBe(2);
    expect(all.works[0].parts[0].parts[0].slug).toBe("g");
    expect(repertoire(works, edges, "scherzo", 2, 1).works.map(w=>w.slug)).toEqual(["b"]);
    expect(repertoire(works, edges, "etude", 1, 1).works[0].slug).toBe("l");
  });
  it("does not hide works behind invalid cyclic relations", () => {
    const rows = [work("a","Scherzo"), work("b","Ballade")];
    const edges = [{parent_slug:"a",child_slug:"b",position:1},{parent_slug:"b",child_slug:"a",position:1}];
    expect(repertoire(rows, edges, undefined, 1, 10).count).toBe(2);
  });
  it("displays both catalogue entries of Chopin's funeral march as one movement under Op. 35", () => {
    const slug = "wikidata-q284448", numbered = "component-wikidata-q284448-3", alternate = "wikidata-q116431346";
    const rows = [work(slug,"Piano Sonata No. 2"),work(numbered,"Marche funebre. Lento"),work(alternate,"Marche funèbre in B-flat minor")];
    const edges = [ {parent_slug:slug,child_slug:numbered,position:3}, {parent_slug:slug,child_slug:alternate,position:null} ];
    const result = repertoire(rows, edges, undefined, 1, 10);
    expect(result.works[0].parts).toHaveLength(1);
    expect(result.works[0].parts[0].alternate?.slug).toBe(alternate);
    expect(result.componentCount).toBe(1);
    expect(repertoire(rows.slice(0,1).concat(rows[2]), edges, undefined, 1, 10).works[0].parts[0].slug).toBe(alternate);
  });
});
