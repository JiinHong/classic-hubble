import { getCatalogWorkBySlug } from "@/lib/catalog";
import { SEARCH_PAGE_SIZE, workForCard } from "@/lib/catalog-search";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const slug = params.get("work") ?? "";
  const offset = Number(params.get("offset") ?? 0);
  const headers = { "Cache-Control": "no-store" };
  if (!/^[a-z0-9-]{1,160}$/.test(slug) || !Number.isSafeInteger(offset) || offset < 0 || offset > 1_000_000)
    return Response.json({ error: "invalid_request" }, { status: 400, headers });
  try {
    const { work, performances } = await getCatalogWorkBySlug(slug);
    if (!work) return Response.json({ error: "not_found" }, { status: 404, headers });
    return Response.json({
      works: [workForCard(work)], performances: performances.slice(offset, offset + SEARCH_PAGE_SIZE),
      total: performances.length, hasMore: offset + SEARCH_PAGE_SIZE < performances.length,
    }, { headers });
  } catch {
    return Response.json({ error: "unavailable" }, { status: 503, headers });
  }
}
