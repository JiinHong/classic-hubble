import { findWorksByQueryInList, getWorkSearchAnchor } from "@classic-hubble/shared";
import { unstable_cache } from "next/cache";
import workComponents from "@/data/work-components.json";
import { createSupabaseClient } from "./supabase/client";
import { attachWorkComponents } from "./work-components";
import {
  SEARCH_PAGE_SIZE,
  workForCard,
  type CatalogSearchResult,
} from "./catalog-search";
import {
  getRelatedWorkSlugs,
  mapPerformances,
  mapWorks,
  PERFORMANCE_COLUMNS,
  WORK_COLUMNS,
  type PerformanceRow,
  type WorkRow,
} from "./catalog";

type Candidate = WorkRow & { id: string };
const emptyResult = (): CatalogSearchResult => ({
  works: [], performances: [], total: 0, hasMore: false,
});

async function readWorkSearchPage(query: string, offset: number): Promise<CatalogSearchResult> {
  const anchor = getWorkSearchAnchor(query);
  if (query && !anchor) return emptyResult();
  const db = createSupabaseClient();
  let rows: Candidate[] = [];
  let total = 0;
  if (!query) {
    const result = await db.from("works")
      .select(`id, ${WORK_COLUMNS}`, { count: "exact" })
      .order("popularity_rank", { ascending: true, nullsFirst: false })
      .order("id")
      .range(offset, offset + SEARCH_PAGE_SIZE - 1);
    if (result.error || result.count === null) throw new Error("Work browse query failed");
    rows = result.data as unknown as Candidate[];
    total = result.count;
  } else {
    for (let start = 0; ; start += 1000) {
      const result = await db.rpc("search_work_candidates", { search_term: anchor })
        .select(`id, ${WORK_COLUMNS}`)
        .order("popularity_rank", { ascending: true, nullsFirst: false })
        .order("id").range(start, start + 999);
      if (result.error) throw new Error("Work candidate query failed");
      const page = result.data as unknown as Candidate[];
      rows.push(...page);
      if (page.length < 1000) break;
    }
  }

  const displayed = new Set(rows.map(row => row.slug));
  // Position labels exist only in component context, not in the original work rows.
  const positionSeeds = query
    ? workComponents.filter(relation => relation.position !== null &&
        [`${relation.position}번`, `no ${relation.position}`].some(label => label.includes(anchor)),
      ).map(relation => relation.child_slug)
    : [];
  const missing = getRelatedWorkSlugs([...displayed, ...positionSeeds]).filter(slug => !displayed.has(slug));
  for (let start = 0; start < missing.length; start += 100) {
    const result = await db.from("works")
      .select(`id, ${WORK_COLUMNS}`)
      .in("slug", missing.slice(start, start + 100));
    if (result.error) throw new Error("Related work query failed");
    rows.push(...result.data as unknown as Candidate[]);
  }
  const candidates = attachWorkComponents(mapWorks(rows, []), workComponents);
  // Preserve the old catalog's popularity/id tie order after family expansion.
  const rowBySlug = new Map(rows.map(row => [row.slug, row]));
  if (query) {
    candidates.sort((a, b) =>
      (a.popularityRank ?? Number.MAX_SAFE_INTEGER) - (b.popularityRank ?? Number.MAX_SAFE_INTEGER) ||
      rowBySlug.get(a.slug)!.id.localeCompare(rowBySlug.get(b.slug)!.id),
    );
  }
  const ranked = query
    ? findWorksByQueryInList(candidates, query)
    : candidates.filter(work => displayed.has(work.slug));
  if (query) total = ranked.length;
  const page = query ? ranked.slice(offset, offset + SEARCH_PAGE_SIZE) : ranked;
  const linksById = new Map<string, Set<string>>();
  if (page.length) {
    const workIds = page.map(work => rowBySlug.get(work.slug)!.id);
    for (let start = 0; ; start += 1000) {
      const result = await db.rpc("work_upcoming_links", { work_ids: workIds })
        .order("work_id").order("performance_id").range(start, start + 999);
      if (result.error) throw new Error("Upcoming work links query failed");
      const links = result.data as { work_id: string; performance_id: string }[];
      for (const link of links) {
        const ids = linksById.get(link.work_id) ?? new Set<string>();
        ids.add(link.performance_id);
        linksById.set(link.work_id, ids);
      }
      if (links.length < 1000) break;
    }
  }
  return {
    works: page.map(work => workForCard({
      ...work,
      upcomingPerformanceIds: [...(linksById.get(rowBySlug.get(work.slug)!.id) ?? [])],
    })),
    performances: [], total, hasMore: offset + SEARCH_PAGE_SIZE < total,
  };
}

const cachedWorkSearchPage = unstable_cache(
  readWorkSearchPage, ["targeted-work-search-v1"], { revalidate: 60 },
);
export function getWorkSearchPage(query = "", offset = 0) {
  return cachedWorkSearchPage(query.trim(), offset);
}

export const getHomeOverview = unstable_cache(async () => {
  const db = createSupabaseClient();
  const summary = await db.rpc("home_catalog_overview");
  if (summary.error || !summary.data?.[0]) throw new Error("Home overview query failed");
  const row = summary.data[0] as {
    work_count: number; upcoming_count: number; confirmed_count: number; performance_ids: string[];
  };
  let performances: PerformanceRow[] = [];
  if (row.performance_ids.length) {
    const result = await db.from("performances")
      .select(`id, ${PERFORMANCE_COLUMNS}`).in("id", row.performance_ids);
    if (result.error) throw new Error("Home performances query failed");
    const byId = new Map(
      (result.data as unknown as (PerformanceRow & { id: string })[]).map(item => [item.id, item]),
    );
    performances = row.performance_ids.flatMap(id => byId.has(id) ? [byId.get(id)!] : []);
  }
  return {
    workCount: Number(row.work_count),
    upcomingCount: Number(row.upcoming_count),
    confirmedCount: Number(row.confirmed_count),
    performances: mapPerformances(performances),
  };
}, ["targeted-home-overview-v1"], { revalidate: 60 });
