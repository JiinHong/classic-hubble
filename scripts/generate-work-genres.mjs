// Refresh public, CC0 Wikidata genre claims offline; never fetch them in page requests.
import { readFile, writeFile, rename } from "node:fs/promises";
import { setTimeout as delay } from "node:timers/promises";

const data = new URL("../apps/web/src/data/", import.meta.url);
const registry = JSON.parse(await readFile(new URL("composer-korean-name-provenance.json", data)));
const people = [...new Set(Object.values(registry).map(person => {
  const link = person.sources.find(source => source.publisher === "Wikidata")?.url;
  const id = link?.match(/\/(Q[1-9]\d*)$/)?.[1];
  if (!id) throw Error("Missing composer identity");
  return id;
}))].sort();
const groups = new Map();
for (let i = 0; i < people.length; i += 15) {
  const values = people.slice(i, i + 15).map(id => "wd:" + id).join(" ");
  const query = `SELECT DISTINCT ?work ?genre ?genreLabel WHERE {
    VALUES ?composer { ${values} }
    ?work wdt:P86 ?composer; wdt:P31 wd:Q105543609; (wdt:P7937|wdt:P136) ?genre.
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
  }`;
  const url = new URL("https://query.wikidata.org/sparql");
  url.search = new URLSearchParams({ query, format: "json" }).toString();
  const response = await fetch(url, { headers: { "User-Agent": "ClassicHubble/1.0 (https://classichubble.com)" }, signal: AbortSignal.timeout(90000) });
  if (!response.ok) throw Error("Wikidata returned " + response.status);
  const rows = (await response.json()).results.bindings;
  for (const { work, genre, genreLabel } of rows) {
    const id = Number(work.value.match(/\/Q(\d+)$/)[1]);
    const key = genre.value.match(/\/(Q\d+)$/)[1];
    const group = groups.get(key) ?? { label: genreLabel.value, works: new Set() };
    group.works.add(id);
    groups.set(key, group);
  }
  console.log(`${Math.min(i + 15, people.length)}/${people.length} composers`);
  await delay(500);
}
const entries = Object.fromEntries([...groups].sort(([a],[b]) => a.localeCompare(b)).map(([key, group]) =>
  [key, { label: group.label, works: [...group.works].sort((a,b) => a-b) }]));
const dest = new URL("work-genre-claims.json", data);
const tmp = new URL("work-genre-claims.tmp", data);
await writeFile(tmp, JSON.stringify(entries, null, 0) + "\n");
await rename(tmp, dest);
