import { unstable_cache } from "next/cache";
import { mapPerformances, PERFORMANCE_COLUMNS, type PerformanceRow } from "./catalog";
import { searchCatalog } from "./catalog-search";
import { createSupabaseClient } from "./supabase/client";
import { readRankedWorkCandidates } from "./work-candidates";

const SEARCH_COLUMNS = `id, kopis_performance_id, title, starts_at, ends_on, status, artists,
  venues(name, city), program_items(display_title, composer_name, source_type, confidence,
    position, source_provider, works(slug))`;
type SearchRow = Pick<PerformanceRow, "kopis_performance_id" | "title" | "starts_at" | "ends_on" | "status" | "artists" | "venues" | "program_items"> & { id: string };

const readPerformanceSearchPage = unstable_cache(async (query: string, city: string, offset: number) => {
  const db = createSupabaseClient();
  const { works, rows } = query ? await readRankedWorkCandidates(db, query) : { works: [], rows: [] };
  const matchedSlugs = new Set(works.map(work => work.slug));
  const matchedIds = rows.filter(row => matchedSlugs.has(row.slug)).map(row => row.id);
  const rowsToSearch: SearchRow[] = [];
  for (let start = 0; ; start += 1000) {
    const result = await db.rpc("search_performance_candidates", {
      search_term: query.toLowerCase(), city_name: city, matched_work_ids: matchedIds,
    }).select(SEARCH_COLUMNS).order("starts_at").order("id").range(start, start + 999);
    if (result.error) throw new Error("Performance candidate query failed", { cause: result.error });
    const page = result.data as unknown as SearchRow[];
    rowsToSearch.push(...page);
    if (page.length < 1000) break;
  }
  const visibleRows = rowsToSearch.filter(row => !row.kopis_performance_id?.startsWith("perf-"));
  const performances = mapPerformances(visibleRows.map(row => ({
    ...row, booking_url: null, poster_url: null, price_range: null, program_image_urls: [],
    program_source_url: null, program_status: null, source_label: null,
  })));
  const internalIds = new Map(performances.map((item, i) => [item, visibleRows[i].id]));
  const result = searchCatalog({ works, performances }, { query, city, offset, mode: "performances" });
  if (!result.performances.length) return result;
  // Hydrate only the displayed page; search metadata never escapes as a partial card.
  const ids = result.performances.map(item => internalIds.get(item)!);
  const details = await db.from("performances").select(`id, ${PERFORMANCE_COLUMNS}`).in("id", ids);
  if (details.error) throw new Error("Performance details query failed", { cause: details.error });
  const byId = new Map((details.data as unknown as (PerformanceRow & { id: string })[]).map(row => [row.id, row]));
  const ordered = ids.map(id => {
    const row = byId.get(id);
    if (!row) throw new Error("Performance changed during search");
    return row;
  });
  return { ...result, performances: mapPerformances(ordered) };
}, ["targeted-performance-search-v1"], { revalidate: 60 });

export function getPerformanceSearchPage(query = "", city = "전체", offset = 0) {
  return readPerformanceSearchPage(query.trim(), city, offset);
}
