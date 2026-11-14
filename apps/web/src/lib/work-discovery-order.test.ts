import { expect, it } from "vitest";
import { orderForWorkDiscovery } from "./work-discovery-order";

const hits = ["suite", "song", "wikidata-q29117946", "other"].map(slug => ({ slug }));

it.each(["달빛", " CLAIR de LUNE "])("promotes the matched piano movement without dropping other hits: %s", query => {
  expect(orderForWorkDiscovery(hits, query)).toEqual([hits[2], hits[0], hits[1], hits[3]]);
});

it("leaves composer-qualified queries, partial titles and missing matches alone", () => {
  for (const query of ["포레 달빛", "드뷔시 달빛", "달", "manhattan", ""]) {
    expect(orderForWorkDiscovery(hits, query)).toBe(hits);
  }
  const songs = hits.slice(0, 2);
  expect(orderForWorkDiscovery(songs, "달빛")).toBe(songs);
});
