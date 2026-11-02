import { unstable_cache } from "next/cache";
import { createSupabaseClient } from "./supabase/client";
import { expandWorkFamilies, readWorkCandidates } from "./work-candidates";
import { identifyYouTubeWorks } from "./youtube-matching";

const identify = unstable_cache(async (title: string, description: string) => {
  const db = createSupabaseClient();
  const rows = await readWorkCandidates(db, "youtube_work_candidates", { video_text: `${title}\n${description}` });
  const works = await expandWorkFamilies(db, rows);
  const result = identifyYouTubeWorks({ title, description }, works);
  const selected = new Map(result.entries.flatMap(entry => entry.candidates.map(({ work }) => [work.slug, work] as const)));
  const selectedRows = rows.filter(row => selected.has(row.slug));
  const links = new Map<string, Set<string>>();
  // The RPC orders each work's links by the same Seoul-date ordering as mapWorks.
  for (let chunk = 0; chunk < selectedRows.length; chunk += 100) {
    for (let start = 0; ; start += 1000) {
      const response = await db.rpc("youtube_upcoming_links", { work_ids: selectedRows.slice(chunk, chunk + 100).map(row => row.id) })
        .range(start, start + 999);
      if (response.error) throw new Error("YouTube upcoming links query failed");
      const page = response.data as { work_id: string; performance_id: string }[];
      for (const link of page) {
        const ids = links.get(link.work_id) ?? new Set<string>();
        ids.add(link.performance_id);
        links.set(link.work_id, ids);
      }
      if (page.length < 1000) break;
    }
  }
  for (const row of selectedRows) selected.get(row.slug)!.upcomingPerformanceIds = [...(links.get(row.id) ?? [])];
  return result;
}, ["targeted-youtube-identification-v1"], { revalidate: 60 });

export function identifyYouTubeFromDatabase(video: { title: string; description: string }) {
  return identify(video.title, video.description);
}
