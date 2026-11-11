import { getSelectedConcertPage } from "@/lib/performance-search";
import { concertPeriod } from "@/lib/catalog-search";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const slug = params.get("work") ?? "";
  const offset = Number(params.get("offset") ?? 0);
  const city = params.get("city") ?? "전체";
  const period = params.get("period") ?? "all";
  const headers = { "Cache-Control": "no-store" };
  if (!/^[a-z0-9-]{1,160}$/.test(slug) || !Number.isSafeInteger(offset) || offset < 0 || offset > 1_000_000 || city.length > 80 || concertPeriod(period) !== period)
    return Response.json({ error: "invalid_request" }, { status: 400, headers });
  try {
    const page = await getSelectedConcertPage(slug, city, offset, period);
    if (!page) return Response.json({ error: "not_found" }, { status: 404, headers });
    return Response.json(page, { headers });
  } catch {
    return Response.json({ error: "unavailable" }, { status: 503, headers });
  }
}
