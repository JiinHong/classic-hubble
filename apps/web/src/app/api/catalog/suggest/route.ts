import { getWorkSuggestions } from "@/lib/work-suggestions";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const query = new URL(request.url).searchParams.get("q") ?? "";
  const headers = { "Cache-Control": "no-store" };
  if (query.length > 200) return Response.json({ error: "invalid_request" }, { status: 400, headers });
  const start = performance.now();
  try {
    return Response.json({ suggestions: await getWorkSuggestions(query) }, { headers: {
      ...headers,
      "Vercel-CDN-Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
      "Server-Timing": `suggest;dur=${(performance.now() - start).toFixed(1)}`,
    } });
  } catch {
    return Response.json({ error: "unavailable" }, { status: 503, headers });
  }
}
