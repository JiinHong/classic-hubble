import { getCatalogSelection } from "@/lib/catalog";
import { workForCard } from "@/lib/catalog-search";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const slugs = new URL(request.url).searchParams.getAll("slug");
  const headers = { "Cache-Control": "no-store" };
  if (
    slugs.length > 100 ||
    slugs.some((slug) => !/^[a-z0-9-]{1,160}$/.test(slug))
  )
    return Response.json(
      { error: "invalid_request" },
      { status: 400, headers },
    );
  if (!slugs.length)
    return Response.json({ works: [], performances: [] }, { headers });
  try {
    const selection = await getCatalogSelection([...new Set(slugs)]);
    return Response.json(
      {
        works: selection.works.map(workForCard),
        performances: selection.performances,
      },
      { headers },
    );
  } catch {
    return Response.json({ error: "unavailable" }, { status: 503, headers });
  }
}
