import { createYouTubeHandler } from "@/lib/youtube-server";
import { workForCard } from "@/lib/catalog-search";
import { identifyYouTubeFromDatabase } from "@/lib/youtube-candidates";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const getMetadata = createYouTubeHandler({
  apiKey: () => process.env.YOUTUBE_API_KEY,
});

export async function POST(request: Request) {
  const response = await getMetadata(request);
  if (!response.ok) return response;
  const { video } = await response.json();
  const started = performance.now();
  let result;
  try {
    result = await identifyYouTubeFromDatabase(video);
  } catch {
    return Response.json(
      { error: "catalog_unavailable" },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
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
    { headers: { "Cache-Control": "no-store", "Server-Timing": `identification;dur=${(performance.now() - started).toFixed(1)}` } },
  );
}
