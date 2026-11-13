// Public navigation hints only. The live suggestion/search APIs remain authoritative.
import { gzipSync } from "node:zlib";
import { rename, writeFile } from "node:fs/promises";

const phrases = ["베토벤", "쇼팽", "바흐", "브람스", "모차르트", "라흐마니노프",
  "차이콥스키", "드보르자크", "슈베르트", "슈만", "비발디", "리스트", "멘델스존",
  "운명", "신세계", "라흐 피협 2번", "브바협", "피협"];
const keys = new Set(phrases.flatMap(s => [s.slice(0, 1), s.slice(0, 2), s]));
const snapshot = Object.create(null);
for (const key of keys) {
  const url = new URL("/api/catalog/suggest", "https://classichubble.com");
  url.searchParams.set("q", key);
  const response = await fetch(url, { signal: AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error(`HTTP ${response.status} for ${key}`);
  const { suggestions } = await response.json();
  if (!Array.isArray(suggestions) || suggestions.length > 8 || suggestions.some(row =>
    !row || !/^[a-z0-9-]{1,160}$/.test(row.slug) || ![row.title, row.composer].every(v => typeof v === "string" && v.length > 0)))
    throw new Error(`Unexpected suggestion payload for ${key}`);
  if (suggestions.length) snapshot[key] = suggestions.map(({slug, title, composer}) => ({slug, title, composer}));
}
const json = JSON.stringify(snapshot) + "\n";
if (!Object.keys(snapshot).length || gzipSync(json).length > 8192) throw new Error("Invalid starter dictionary size");
const out = new URL("../src/data/starter-suggestions.json", import.meta.url);
const temp = new URL(out.href + ".tmp");
await writeFile(temp, json);
await rename(temp, out);
console.log(`Generated ${Object.keys(snapshot).length} keys, ${gzipSync(json).length} bytes gzipped`);
