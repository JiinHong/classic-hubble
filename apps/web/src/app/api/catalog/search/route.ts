import { getPerformanceSearchPage } from "@/lib/performance-search";
import { getWorkSearchPage } from "@/lib/work-search";
import { concertPeriod } from "@/lib/catalog-search";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const query = params.get("q") ?? "";
  const city = params.get("city") ?? "전체";
  const mode = params.get("mode") ?? "works";
  const offset = Number(params.get("offset") ?? 0);
  const period = params.get("period") ?? "all";
  if (
    query.length > 200 ||
    city.length > 80 ||
    !["works", "performances"].includes(mode) ||
    concertPeriod(period) !== period ||
    !Number.isSafeInteger(offset) ||
    offset < 0 ||
    offset > 1_000_000
  ) {
    return Response.json({ error: "invalid_request" }, { status: 400 });
  }
  const startedAt = performance.now();
  try {
    let result;
    let timing;
    if (mode === "works") {
      result = await getWorkSearchPage(query, offset);
      timing = `targeted;dur=${(performance.now() - startedAt).toFixed(1)}`;
    } else {
      result = await getPerformanceSearchPage(query, city, offset, period);
      timing = `targeted;dur=${(performance.now() - startedAt).toFixed(1)}`;
    }
    return Response.json(result, {
      headers: {
        "Cache-Control": "no-store",
        // This endpoint contains only anonymous catalog data, never user libraries.
        "Vercel-CDN-Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
        "Server-Timing": timing,
      },
    });
  } catch {
    return Response.json(
      { error: "unavailable" },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
}
