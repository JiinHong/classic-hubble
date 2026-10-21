import { getCatalogSnapshot } from "@/lib/catalog";
import { searchCatalog } from "@/lib/catalog-search";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const query = params.get("q") ?? "";
  const city = params.get("city") ?? "전체";
  const mode = params.get("mode") ?? "works";
  const offset = Number(params.get("offset") ?? 0);
  if (
    query.length > 200 ||
    city.length > 80 ||
    !["works", "performances"].includes(mode) ||
    !Number.isSafeInteger(offset) ||
    offset < 0 ||
    offset > 1_000_000
  ) {
    return Response.json({ error: "invalid_request" }, { status: 400 });
  }
  const catalog = await getCatalogSnapshot();
  if (catalog.source === "unavailable")
    return Response.json(
      { error: "unavailable" },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  return Response.json(
    searchCatalog(catalog, {
      query,
      city,
      mode: mode as "works" | "performances",
      offset,
    }),
    { headers: { "Cache-Control": "no-store" } },
  );
}
