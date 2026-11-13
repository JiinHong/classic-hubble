import { unstable_cache } from "next/cache";
import baseline from "@/data/openopus-composers.json";
import relations from "@/data/work-components.json";
import { repertoire, type WorkRow } from "./composer-repertoire";
import type { Form } from "./work-forms";
import { composerIdentityKey, toComposerDirectoryEntry } from "./composer-directory";
import { createSupabaseClient, isSupabaseConfigured } from "./supabase/client";

export const PROFILE_PAGE_SIZE = 24;
const uuid = /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i;
const originals = new Map(baseline.map(row => ["openopus:" + composerIdentityKey(row.name), row]));

const getComposerIndex = unstable_cache(async (id: string) => {
  const original = originals.get(id);
  if (!isSupabaseConfigured) throw new Error("Public catalog unavailable");
  const db = createSupabaseClient();
  const byIdentity = db.from("composers").select("id,name,name_ko,period");
  const person = await (original ? byIdentity.eq("name", original.name) : byIdentity.eq("id", id)).maybeSingle();
  if (person.error) throw new Error("Could not load composer");
  if (!person.data) {
    if (!original) return null;
    return { composer: toComposerDirectoryEntry({ ...original, id }), rows: [] as WorkRow[] };
  }
  const row = person.data;
  const composer = toComposerDirectoryEntry({ id: row.id, name: row.name, nameKo: row.name_ko, period: row.period });
  const rows: WorkRow[] = [];
  let total: number | null = null;
  for (let offset = 0; ; offset += 500) {
    const { data, error, count } = await db.from("works").select("slug,title,title_ko,catalogue,instrumentation", offset === 0 ? { count: "exact" } : {})
      .eq("composer_id", row.id).order("popularity_rank", { ascending: true, nullsFirst: false })
      .order("title_ko", { ascending: true, nullsFirst: false }).order("title").order("slug").range(offset, offset + 499);
    if (error || !data) throw new Error("Could not load composer works");
    rows.push(...data);
    total ??= count;
    if (data.length < 500 || (total != null && rows.length >= total)) break;
  }
  return { composer, rows };
}, ["composer-repertoire-index-v1", process.env.NEXT_PUBLIC_SUPABASE_URL ?? ""], { revalidate: 300 });

export async function getComposerProfile(id: string, page: number, genre?: Form) {
  if ((!originals.has(id) && !uuid.test(id)) || !Number.isSafeInteger(page) || page < 1 || page > 10000) return null;
  const index = await getComposerIndex(id);
  return index && { composer: index.composer, ...repertoire(index.rows, relations, genre, page, PROFILE_PAGE_SIZE, index.composer.name) };
}
