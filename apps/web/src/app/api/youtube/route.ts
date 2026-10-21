import { createYouTubeHandler } from "@/lib/youtube-server";
import { getCatalogSnapshot } from "@/lib/catalog";
import { workForCard } from "@/lib/catalog-search";
import { identifyYouTubeWorks } from "@/lib/youtube-matching";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const getMetadata = createYouTubeHandler({
  apiKey: () => process.env.YOUTUBE_API_KEY,
});

export async function POST(request: Request) {
  const response = await getMetadata(request);
  if (!response.ok) return response;
  const { video } = await response.json();
  const catalog = await getCatalogSnapshot();
  if (catalog.source === "unavailable")
    return Response.json(
      { error: "catalog_unavailable" },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  const result = identifyYouTubeWorks(video, catalog.works);
  return Response.json(
    {
      video,
      result: {
        entries: result.entries.map((entry) => ({
          ...entry,
          candidates: entry.candidates.map((candidate) => ({
            ...candidate,
            work: workForCard(candidate.work),
          })),
        })),
      },
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
