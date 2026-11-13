import { describe, expect, it } from "vitest";
import { matchComposers } from "./composer-search";

describe("composer typeahead", () => {
  it.each(["쇼팽", " CHOPIN ", "frederic chopin"])("resolves the exact identity for %s", query => {
    expect(matchComposers(query).exact?.name).toBe("Frédéric Chopin");
  });
  it.each(["바흐", "Bach", "슈만"])("never picks one person for the shared surname %s", query => {
    expect(matchComposers(query).exact).toBeNull();
    expect(matchComposers(query).matches.length).toBeGreaterThan(0);
  });
  it("suggests the person for a prefix but does not redirect until confirmed", () => {
    expect(matchComposers("모차").matches[0]?.name).toBe("Wolfgang Amadeus Mozart");
    expect(matchComposers("모차").exact).toBeNull();
  });
  it.each(["모차르트 레퀴엠", "", "Op. 9", "Traditional"])("does not consume a work query or non-person credit: %s", query => {
    expect(matchComposers(query)).toEqual({ matches: [], exact: null });
  });
});
