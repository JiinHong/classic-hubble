// Public navigation hints only. Never include works or private user fields here.
import { readFile, rename, writeFile } from "node:fs/promises";
import { gzipSync } from "node:zlib";

const base = new URL(process.env.NEXT_PUBLIC_SUPABASE_URL);
if (base.hostname !== "klnfamtwxwrelrjeguqb.supabase.co") throw new Error("Unexpected catalog");
const apikey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
if (!apikey) throw new Error("Set the public Supabase key");
const folder = new URL("../src/data/", import.meta.url);
const baseline = JSON.parse(await readFile(new URL("openopus-composers.json", folder), "utf8"));
const key = s => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().trim();
const entries = new Map();
const liveNames = new Set();
const url = new URL("/rest/v1/composers", base);
url.search = "select=id,name,name_ko,period&order=id&limit=500";
for (let offset = 0; ; offset += 500) {
  url.searchParams.set("offset", String(offset));
  const resp = await fetch(url, { headers: { apikey }, signal: AbortSignal.timeout(15000) });
  if (!resp.ok) throw new Error("Catalog unavailable: " + resp.status);
  const rows = await resp.json();
  for (const { id, name, name_ko, period } of rows) {
    if (!id || !name) throw new Error("Incomplete public identity");
    entries.set(id, [id, name, name_ko, period]);
    liveNames.add(key(name));
  }
  if (rows.length < 500) break;
}
if (!entries.size) throw new Error("Refusing to replace index with empty catalog");
for (const { name, nameKo, period } of baseline) {
  if (!liveNames.has(key(name))) {
    const id = "openopus:" + key(name);
    entries.set(id, [id, name, nameKo, period]);
  }
}
const json = JSON.stringify([...entries.values()]) + "\n";
if (gzipSync(json).length > 32768) throw new Error("Review composer index size budget");
const out = new URL("composer-index.json", folder);
const tmp = new URL(out.href + ".tmp");
await writeFile(tmp, json);
await rename(tmp, out);
console.log(entries.size + " composers, " + gzipSync(json).length + " bytes compressed");
