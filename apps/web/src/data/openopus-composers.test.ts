import { describe, expect, it } from "vitest";

import composers from "./openopus-composers.json";

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
      expect(composer.nameKo).toBeNull();
    }
  });
});
