// Use only the 220 reviewed Open Opus identities, never search by surname for an image.
import { readFile, writeFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const sharp = createRequire(require.resolve("next/package.json"))("sharp");
const folder = new URL("../src/data/", import.meta.url);
const raw = JSON.parse(await readFile(new URL("composer-korean-name-provenance.json", folder), "utf8"));
const portraits = new URL("../public/composer-portraits/", import.meta.url);
const existing = new Set((await readdir(portraits)).filter(s => s.endsWith(".jpg")));
const slug = s => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().replace(/['’]/g, "").replace(/\s+/g, "-");
// Open Opus uses distinct filenames for family members and compound names.
const special = { "Alessandro Marcello": "marcello-a", "Alessandro Scarlatti": "scarlatti-a",
  "Carl Philipp Emanuel Bach": "bach-cpe", "Johann Christian Bach": "bach-jc",
  "Johann Strauss Jr": "strauss-jr", "Camargo Guarnieri": "camargo-guarnieri",
  "Joly Braga Santos": "braga-santos", "Josquin Des Prez": "des-prez",
  "Ralph Vaughan Williams": "vaughan-williams", "Sergei Rachmaninoff": "rachmaninov" };
const dir = process.argv[2];
if (!dir) throw new Error("Pass the portraits directory from the pinned Open Opus release (see docs/data-sources.md)");
const metadata = {};
const consumed = new Set();
for (const name of Object.keys(raw)) {
  const stem = special[name] ?? slug(name.split(" ").at(-1));
  if (consumed.has(stem)) throw new Error("Ambiguous portrait: " + name);
  consumed.add(stem);
  const out = slug(name);
  if (!existing.has(out + ".jpg")) {
    await sharp(join(dir, stem + ".png")).resize(200, 200, { fit: "cover" }).webp({ quality: 82 }).toFile(new URL(out + ".webp", portraits).pathname);
  }
  metadata[name] = out + (existing.has(out + ".jpg") ? ".jpg" : ".webp");
}
await writeFile(new URL("composer-portrait-files.json", folder), JSON.stringify(metadata, null, 2) + "\n");
const ids = Object.entries(raw).map(([name, info]) => {
  const url = info.sources.find(s => s.publisher === "Wikidata")?.url;
  const id = url?.match(/^https:\/\/www\.wikidata\.org\/(?:entity|wiki)\/(Q\d+)$/)?.[1];
  if (!id) throw new Error("Missing reviewed source for " + name);
  return [name, id];
});
const descriptions = {};
for (let i = 0; i < ids.length; i += 40) {
  const batch = ids.slice(i, i + 40);
  const params = new URLSearchParams({ action: "wbgetentities", format: "json", props: "descriptions", languages: "ko", ids: batch.map(([, id]) => id).join("|") });
  const response = await fetch("https://www.wikidata.org/w/api.php?" + params, { headers: { "User-Agent": "ClassicHubble/1.0 (https://classichubble.com)" }, signal: AbortSignal.timeout(20000) });
  if (!response.ok) throw new Error("Wikidata HTTP " + response.status);
  const { entities } = await response.json();
  for (const [name, id] of batch) {
    const description = entities[id]?.descriptions?.ko?.value;
    if (description) descriptions[name] = { description, id };
  }
}
await writeFile(new URL("composer-descriptions.json", folder), JSON.stringify(descriptions, null, 2) + "\n");
console.log(consumed.size + " local portraits; " + Object.keys(descriptions).length + " sourced Korean descriptions");
