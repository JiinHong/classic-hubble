import { createYouTubeHandler } from "@/lib/youtube-server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const POST = createYouTubeHandler({
  apiKey: () => process.env.YOUTUBE_API_KEY,
});
