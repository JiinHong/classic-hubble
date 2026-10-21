import { describe, expect, it } from "vitest";
import { works } from "@classic-hubble/shared";
import { attachWorkComponents } from "./work-components";

describe("work component relationships", () => {
  const parent = { ...works[0], slug: "parent", upcomingPerformanceIds: ["whole"] };
  const child = { ...works[0], slug: "child", titleKo: "고독한 꽃", upcomingPerformanceIds: ["piece"] };
  const relation = { parent_slug: "parent", child_slug: "child", position: 3 };

  it("links distinct works without inheriting performances or aliases", () => {
    const result = attachWorkComponents([parent, child], [relation]);
    expect(result[0].parts?.[0]).toMatchObject({ slug: "child", position: 3 });
    expect(result[1].partOf?.[0]).toMatchObject({ slug: "parent", position: 3 });
    expect(result[0].upcomingPerformanceIds).toEqual(["whole"]);
    expect(result[1].upcomingPerformanceIds).toEqual(["piece"]);
    expect(result[0].aliases).toEqual(parent.aliases);
    expect(parent).not.toHaveProperty("parts");
  });

  it("ignores dangling, cross-composer and cyclic relationships", () => {
    const other = { ...child, slug: "other", composer: { ...child.composer, id: "other" } };
    const result = attachWorkComponents([parent, child, other], [
      { ...relation, child_slug: "missing" }, { ...relation, child_slug: "other" },
      relation, { parent_slug: "child", child_slug: "parent", position: 1 },
    ]);
    expect(result.every(w => !w.parts?.length && !w.partOf?.length)).toBe(true);
  });
});
