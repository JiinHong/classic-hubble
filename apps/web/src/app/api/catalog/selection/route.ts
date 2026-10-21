import { getUpcomingPerformancesFromList } from "@classic-hubble/shared";
import { getCatalogSnapshot } from "@/lib/catalog";
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
  const catalog = await getCatalogSnapshot();
  if (catalog.source === "unavailable")
    return Response.json({ error: "unavailable" }, { status: 503, headers });
  const selected = new Set(slugs);
  return Response.json(
    {
      works: catalog.works
        .filter((work) => selected.has(work.slug))
        .map(workForCard),
      performances: getUpcomingPerformancesFromList(
        catalog.performances,
      ).filter((performance) =>
        performance.program.some((item) => selected.has(item.workSlug)),
      ),
    },
    { headers },
  );
}
