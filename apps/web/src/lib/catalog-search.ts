import {
  findWorksByQueryInList,
  getUpcomingPerformancesFromList,
  type Performance,
  type Work,
} from "@classic-hubble/shared";

export const SEARCH_PAGE_SIZE = 24;
export type SearchMode = "works" | "performances";
export type CatalogSearchResult = {
  works: Work[];
  performances: Performance[];
  total: number;
  hasMore: boolean;
};

export function workForCard(work: Work): Work {
  return {
    ...work,
    aliases: [],
    parts: [],
    partOf: work.partOf?.map((parent) => ({ ...parent, aliases: undefined })),
  };
}

export function searchCatalog(
  catalog: { works: Work[]; performances: Performance[] },
  {
    query = "",
    mode = "works",
    city = "전체",
    offset = 0,
  }: { query?: string; mode?: SearchMode; city?: string; offset?: number },
): CatalogSearchResult {
  const trimmed = query.trim();
  const works = trimmed
    ? findWorksByQueryInList(catalog.works, trimmed)
    : catalog.works;
  if (mode === "works")
    return {
      works: works.slice(offset, offset + SEARCH_PAGE_SIZE).map(workForCard),
      performances: [],
      total: works.length,
      hasMore: offset + SEARCH_PAGE_SIZE < works.length,
    };
  const slugs = new Set(works.map((work) => work.slug));
  const lowered = trimmed.toLowerCase();
  const performances = getUpcomingPerformancesFromList(
    catalog.performances,
  ).filter((performance) => {
    if (city !== "전체" && performance.city !== city) return false;
    if (!lowered) return true;
    const haystack = [
      performance.title,
      performance.venue,
      performance.city,
      ...performance.artists,
      ...performance.program.flatMap((item) => [
        item.composerName,
        item.displayTitle,
        item.source.label,
      ]),
    ]
      .join(" ")
      .toLowerCase();
    return (
      haystack.includes(lowered) ||
      performance.program.some((item) => slugs.has(item.workSlug))
    );
  });
  return {
    works: [],
    performances: performances.slice(offset, offset + SEARCH_PAGE_SIZE),
    total: performances.length,
    hasMore: offset + SEARCH_PAGE_SIZE < performances.length,
  };
}
