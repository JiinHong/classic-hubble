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
