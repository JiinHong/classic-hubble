import { unstable_cache } from "next/cache";
import baseline from "@/data/openopus-composers.json";
import { composerIdentityKey, toComposerDirectoryEntry } from "./composer-directory";
import { createSupabaseClient, isSupabaseConfigured } from "./supabase/client";

export const PROFILE_PAGE_SIZE = 24;
type Work = { slug: string; title: string; title_ko: string | null; catalogue: string | null };
const uuid = /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i;
const originals = new Map(baseline.map(row => ["openopus:" + composerIdentityKey(row.name), row]));

export const getComposerProfile = unstable_cache(async (id: string, page: number) => {
  const original = originals.get(id);
  if ((!original && !uuid.test(id)) || !Number.isSafeInteger(page) || page < 1 || page > 10000) return null;
  if (!isSupabaseConfigured) throw new Error("Public catalog unavailable");
  const db = createSupabaseClient();
  const byIdentity = db.from("composers").select("id,name,name_ko,period");
  const person = await (original ? byIdentity.eq("name", original.name) : byIdentity.eq("id", id)).maybeSingle();
  if (person.error) throw new Error("Could not load composer");
  if (!person.data) {
    if (!original) return null;
    return { composer: toComposerDirectoryEntry({ ...original, id }), count: 0, works: [] as Work[] };
  }
  const row = person.data;
  const composer = toComposerDirectoryEntry({ id: row.id, name: row.name, nameKo: row.name_ko, period: row.period });
  const offset = (page - 1) * PROFILE_PAGE_SIZE;
  const { count, data, error } = await db.from("works").select("slug,title,title_ko,catalogue", { count: "exact" })
    .eq("composer_id", row.id).order("popularity_rank", { ascending: true, nullsFirst: false })
    .order("title_ko", { ascending: true, nullsFirst: false }).order("title")
    .order("slug").range(offset, offset + PROFILE_PAGE_SIZE - 1);
  if (error && error.code !== "PGRST103") throw new Error("Could not load composer works");
  if (error) return null;
  if (count == null || !data) throw new Error("Incomplete composer works response");
  return { composer, count, works: data as Work[] };
}, ["public-composer-profile-v1", process.env.NEXT_PUBLIC_SUPABASE_URL ?? ""], { revalidate: 300 });
