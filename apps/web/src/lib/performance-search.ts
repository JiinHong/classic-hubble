import { unstable_cache } from "next/cache";
import { mapPerformances, mapWorks, PERFORMANCE_COLUMNS, WORK_COLUMNS, type PerformanceRow, type WorkRow } from "./catalog";
import { workForCard, type CatalogSearchResult, type ConcertPeriod } from "./catalog-search";
import { createSupabaseClient } from "./supabase/client";
import { readRankedWorkCandidates } from "./work-candidates";

// Ranking depends on the term, not the requested page, region or date filter.
const rankedIds = unstable_cache(async (query: string) => {
  const { works, rows } = await readRankedWorkCandidates(createSupabaseClient(), query, "concerts");
  const slugs = new Set(works.map(w => w.slug));
  return rows.filter(r => slugs.has(r.slug)).map(r => r.id);
}, ["concert-ranked-work-ids-v1"], { revalidate: 60 });

type Database = ReturnType<typeof createSupabaseClient>;
type Page = { upcoming_count: number; past_count: number; performance_ids: string[]; match_slugs: (string | null)[]; available_cities: string[] };

async function concertPage(db: Database, query: string | null, ids: string[], city: string, period: ConcertPeriod, offset: number): Promise<CatalogSearchResult> {
  const index = await db.rpc("concert_search_page", { search_term: query, matched_work_ids: ids,
    city_name: city, period_filter: period, page_offset: offset });
  const page = (index.data as Page[] | null)?.[0];
  if (index.error || !page) throw new Error("Concert search failed", { cause: index.error });
  const periodCounts = { upcoming: Number(page.upcoming_count), past: Number(page.past_count) };
  const total = period === "all" ? periodCounts.upcoming + periodCounts.past : periodCounts[period];
  const result: CatalogSearchResult = { works: [], performances: [], total, hasMore: false, periodCounts, matchedWorkSlugs: {}, cities: page.available_cities };
  if (!page.performance_ids.length) return result;
  const details = await db.from("performances").select(`id, ${PERFORMANCE_COLUMNS}`).in("id", page.performance_ids);
  if (details.error) throw new Error("Performance details query failed", { cause: details.error });
  const byId = new Map((details.data as unknown as (PerformanceRow & { id: string })[]).map(r => [r.id, r]));
  const performances = mapPerformances(page.performance_ids.map(id => {
    const r = byId.get(id);
    if (!r) throw new Error("Performance changed during search");
    return r;
  }));
  return { ...result, performances, hasMore: offset + performances.length < total,
    matchedWorkSlugs: Object.fromEntries(performances.flatMap((p,i) => {
      const slug = page.match_slugs[i];
      return slug ? [[p.id,slug]] : [];
    })) };
}

export const getPerformanceSearchPage = unstable_cache(async (query = "", city = "전체", offset = 0, period: ConcertPeriod = "all") => {
  const term = query.trim().normalize("NFC");
  return concertPage(createSupabaseClient(), term, term ? await rankedIds(term) : [], city, period, offset);
}, ["concert-search-history-v1"], { revalidate: 60 });

export const getSelectedConcertPage = unstable_cache(async (slug: string, city: string, offset: number, period: ConcertPeriod) => {
  const db = createSupabaseClient();
  const selected = await db.from("works").select(`id, ${WORK_COLUMNS}`).eq("slug",slug).maybeSingle();
  if (selected.error) throw new Error("Selected work unavailable", { cause: selected.error });
  if (!selected.data) return null;
  const row = selected.data as unknown as WorkRow & { id: string };
  const page = await concertPage(db, null, [row.id], city, period, offset);
  return { ...page, works: [workForCard(mapWorks([row], [])[0])] };
}, ["selected-concert-history-v1"], { revalidate: 60 });
