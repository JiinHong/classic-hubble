import { describe, expect, it } from "vitest";
import relations from "@/data/work-components.json";

describe("published component registry", () => {
  it("keeps Mit Myrten und Rosen under Liederkreis Op.24, not Myrthen Op.25", () => {
    expect(relations.find(r => r.child_slug === "component-wikidata-q6544099-9")).toMatchObject({ parent_slug: "wikidata-q6544099", position: 9 });
  });
  it("has unique, non-self relationships and valid explicit ordinals", () => {
    expect(new Set(relations.map(r => `${r.parent_slug}/${r.child_slug}`)).size).toBe(relations.length);
    for (const relation of relations) {
      expect(relation.parent_slug).not.toBe(relation.child_slug);
      expect(relation.position === null || (Number.isInteger(relation.position) && relation.position > 0)).toBe(true);
      expect(relation.source_url.startsWith("https://")).toBe(true);
    }
  });
  it("includes all nine source-verified Waldszenen pieces", () => {
    const forest = relations.filter(r => r.parent_slug === "wikidata-q3565331");
    expect(forest.map(r => r.position).sort((a, b) => a! - b!)).toEqual([1,2,3,4,5,6,7,8,9]);
    expect(forest.find(r => r.position === 3)?.child_slug).toBe("component-wikidata-q3565331-3");
  });
});
