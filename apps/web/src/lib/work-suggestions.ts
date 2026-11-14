import { normalizeWorkSearchText } from "@classic-hubble/shared";
import { unstable_cache } from "next/cache";
import { orderForWorkDiscovery } from "./work-discovery-order";
import { createSupabaseClient } from "./supabase/client";

export type WorkSuggestion = { slug: string; title: string; composer: string };

const readSuggestions = unstable_cache(async (query: string): Promise<WorkSuggestion[]> => {
  const { data, error } = await createSupabaseClient().rpc("suggest_works_v2", { search_term: query });
  if (error) throw new Error("Work suggestions unavailable");
  return orderForWorkDiscovery((data ?? []) as WorkSuggestion[], query);
}, ["work-suggestions-v3"], { revalidate: 60 });

export function getWorkSuggestions(query: string): Promise<WorkSuggestion[]> {
  const value = query.trim();
  if (!normalizeWorkSearchText(value) || value.length > 200) return Promise.resolve([]);
  return readSuggestions(value);
}
