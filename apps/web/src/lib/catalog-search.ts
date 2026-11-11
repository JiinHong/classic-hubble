import {
  findWorksByQueryInList,
  getUpcomingPerformancesFromList,
  type Performance,
  type Work,
} from "@classic-hubble/shared";

export const SEARCH_PAGE_SIZE = 24;
export type SearchMode = "works" | "performances";
export type ConcertPeriod = "all" | "upcoming" | "past";
export const concertPeriod = (value: unknown): ConcertPeriod => value === "past" || value === "upcoming" ? value : "all";
export type CatalogSearchResult = {
  works: Work[];
  performances: Performance[];
  total: number;
  hasMore: boolean;
  periodCounts?: { upcoming: number; past: number };
  matchedWorkSlugs?: Record<string, string>;
  cities?: string[];
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
    period = "all",
  }: { query?: string; mode?: SearchMode; city?: string; offset?: number; period?: ConcertPeriod },
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
  const matched = catalog.performances.filter((performance) => {
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
  const upcoming = getUpcomingPerformancesFromList(matched);
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(new Date());
  const past = matched.filter(p => (p.endDate ?? p.date) < today).sort((a,b) =>
    (b.endDate ?? b.date).localeCompare(a.endDate ?? a.date) || (b.date+b.time).localeCompare(a.date+a.time));
  const performances = period === "all" ? [...upcoming, ...past] : period === "past" ? past : upcoming;
  const page = performances.slice(offset, offset + SEARCH_PAGE_SIZE);
  return {
    works: [],
    performances: page,
    periodCounts: { upcoming: upcoming.length, past: past.length },
    matchedWorkSlugs: Object.fromEntries(page.flatMap(p => {
      const match = trimmed && p.program.find(i => slugs.has(i.workSlug));
      return match ? [[p.id, match.workSlug]] : [];
    })),
    total: performances.length,
    hasMore: offset + SEARCH_PAGE_SIZE < performances.length,
  };
}
