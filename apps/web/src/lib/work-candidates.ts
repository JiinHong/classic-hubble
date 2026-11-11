import { findWorksByQueryInList, getWorkSearchAnchor } from "@classic-hubble/shared";
import workComponents from "@/data/work-components.json";
import { getRelatedWorkSlugs, mapWorks, WORK_COLUMNS, type WorkRow } from "./catalog";
import { createSupabaseClient } from "./supabase/client";
import { attachWorkComponents } from "./work-components";

export type WorkCandidateRow = WorkRow & { id: string };
type Database = ReturnType<typeof createSupabaseClient>;

export async function readWorkCandidates(db: Database, name: "search_work_candidates" | "concert_rank_work_candidates" | "youtube_work_candidates", args: Record<string, string>) {
  const rows: WorkCandidateRow[] = [];
  for (let start = 0; ; start += 1000) {
    const result = await db.rpc(name, args).select(`id, ${WORK_COLUMNS}`)
      .order("popularity_rank", { ascending: true, nullsFirst: false }).order("id")
      .range(start, start + 999);
    if (result.error) throw new Error("Work candidate query failed", { cause: result.error });
    const page = result.data as unknown as WorkCandidateRow[];
    rows.push(...page);
    if (page.length < 1000) return rows;
  }
}

export async function expandWorkFamilies(db: Database, rows: WorkCandidateRow[], seeds: string[] = []) {
  const present = new Set(rows.map(row => row.slug));
  const missing = getRelatedWorkSlugs([...present, ...seeds]).filter(slug => !present.has(slug));
  for (let start = 0; start < missing.length; start += 100) {
    const result = await db.from("works").select(`id, ${WORK_COLUMNS}`).in("slug", missing.slice(start, start + 100));
    if (result.error) throw new Error("Related work query failed");
    rows.push(...result.data as unknown as WorkCandidateRow[]);
  }
  return attachWorkComponents(mapWorks(rows, []), workComponents);
}

export async function readRankedWorkCandidates(db: Database, query: string, scope: "works" | "concerts" = "works") {
  const anchor = getWorkSearchAnchor(query);
  if (!anchor) return { rows: [] as WorkCandidateRow[], works: [] };
  const rows = scope === "concerts"
    ? await readWorkCandidates(db, "concert_rank_work_candidates", { search_term: anchor, literal_name: query })
    : await readWorkCandidates(db, "search_work_candidates", { search_term: anchor });
  // Synthetic position labels live in component context, not in source work names.
  const seeds = workComponents.filter(relation => relation.position !== null &&
    [`${relation.position}번`, `no ${relation.position}`].some(label => label.includes(anchor)),
  ).map(relation => relation.child_slug);
  const candidates = await expandWorkFamilies(db, rows, seeds);
  const rowBySlug = new Map(rows.map(row => [row.slug, row]));
  candidates.sort((a, b) =>
    (a.popularityRank ?? Number.MAX_SAFE_INTEGER) - (b.popularityRank ?? Number.MAX_SAFE_INTEGER) ||
    rowBySlug.get(a.slug)!.id.localeCompare(rowBySlug.get(b.slug)!.id),
  );
  return { rows, works: findWorksByQueryInList(candidates, query) };
}
