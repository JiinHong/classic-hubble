import {
  getUpcomingPerformancesFromList,
  type ConfidenceLevel,
  type Performance,
  type ProgramPublicationStatus,
  type ReviewItem,
  type Work,
} from "@classic-hubble/shared";

import openOpusComposers from "@/data/openopus-composers.json";

import {
  composerIdentityKey,
  toComposerDirectoryEntry,
  type ComposerDirectoryEntry,
} from "./composer-directory";
import { createSupabaseClient, isSupabaseConfigured } from "./supabase/client";

type SourceType = "supabase" | "unavailable";

type CatalogSnapshot = {
  performances: Performance[];
  reviewQueue: ReviewItem[];
  source: SourceType;
  works: Work[];
};

type Relation<T> = T | T[] | null;

type ComposerRow = {
  id: string;
  name: string;
  name_ko: string | null;
  period: string | null;
};

type ComposerDirectoryRow = {
  id: string;
  name: string;
  name_ko: string | null;
  period: string | null;
};

type WorkRow = {
  catalogue: string | null;
  composers: Relation<ComposerRow>;
  instrumentation: string | null;
  popularity_rank: number | null;
  slug: string;
  title: string;
  title_ko: string | null;
  work_aliases: { alias: string }[] | null;
};

type PerformanceRow = {
  artists: string[] | null;
  booking_url: string | null;
  kopis_performance_id: string | null;
  poster_url: string | null;
  price_range: string | null;
  program_image_urls: string[] | null;
  program_items:
    | {
        composer_name: string | null;
        confidence: number | string;
        display_title: string;
        position: number;
        source_provider: string;
        source_type: ConfidenceLevel;
        works: Relation<{ slug: string }>;
      }[]
    | null;
  program_source_url: string | null;
  program_status: ProgramPublicationStatus | null;
  source_label: string | null;
  starts_at: string;
  ends_on: string | null;
  status: "open" | "upcoming" | "soldout" | "closed";
  title: string;
  venues: Relation<{ city: string; name: string }>;
};

function unavailableSnapshot(): CatalogSnapshot {
  return {
    performances: [],
    reviewQueue: [],
    source: "unavailable",
    works: [],
  };
}

const baselineComposerDirectory = openOpusComposers.map((composer) =>
  toComposerDirectoryEntry({
    id: `openopus:${composerIdentityKey(composer.name)}`,
    name: composer.name,
    nameKo: composer.nameKo,
    period: composer.period,
  }),
);

function copyBaselineComposerDirectory(): ComposerDirectoryEntry[] {
  return baselineComposerDirectory.map((composer) => ({ ...composer }));
}

function mergeComposerRows(
  rows: ComposerDirectoryRow[],
): ComposerDirectoryEntry[] {
  const composersByName = new Map(
    copyBaselineComposerDirectory().map((composer) => [
      composerIdentityKey(composer.name),
      composer,
    ]),
  );

  for (const row of rows) {
    composersByName.set(
      composerIdentityKey(row.name),
      toComposerDirectoryEntry({
        id: row.id,
        name: row.name,
        nameKo: row.name_ko,
        period: row.period,
      }),
    );
  }

  return Array.from(composersByName.values());
}

const COMPOSER_PAGE_SIZE = 1000;

const sourceLabels: Record<ConfidenceLevel, string> = {
  estimated: "추정 매칭",
  official: "공식 확인",
  ocr: "OCR 추출",
  unknown: "확인 필요",
  verified: "검수 완료",
};

function firstRelation<T>(value: Relation<T> | undefined) {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

function datePartsForKorea(value: string) {
  const date = new Date(value);
  const dateFormatter = new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "2-digit",
    timeZone: "Asia/Seoul",
    year: "numeric",
  });
  const dateParts = Object.fromEntries(
    dateFormatter.formatToParts(date).map((part) => [part.type, part.value]),
  );
  const datePart = `${dateParts.year}-${dateParts.month}-${dateParts.day}`;
  const timePart = new Intl.DateTimeFormat("ko-KR", {
    hour: "2-digit",
    hourCycle: "h23",
    minute: "2-digit",
    timeZone: "Asia/Seoul",
  }).format(date);

  return { date: datePart, time: timePart };
}

function mapWorks(rows: WorkRow[], performances: Performance[]): Work[] {
  const performanceIdsByWork = new Map<string, string[]>();

  for (const performance of getUpcomingPerformancesFromList(performances)) {
    const performanceId = performance.id;
    for (const item of performance.program) {
      const slug = item.workSlug;
      if (!slug) continue;

      const ids = performanceIdsByWork.get(slug) ?? [];
      if (!ids.includes(performanceId)) ids.push(performanceId);
      performanceIdsByWork.set(slug, ids);
    }
  }

  return rows.map((row) => {
    const composer = firstRelation(row.composers);

    return {
      aliases: row.work_aliases?.map((alias) => alias.alias) ?? [],
      catalogue: row.catalogue ?? "",
      composer: {
        id: composer?.id ?? row.slug,
        name: composer?.name ?? "",
        nameKo: composer?.name_ko ?? composer?.name ?? "",
        period: composer?.period ?? "",
      },
      instrumentation: row.instrumentation ?? "",
      popularityRank: row.popularity_rank ?? 999,
      slug: row.slug,
      title: row.title,
      titleKo: row.title_ko ?? row.title,
      upcomingPerformanceIds: performanceIdsByWork.get(row.slug) ?? [],
    };
  });
}

function mapPerformances(rows: PerformanceRow[]): Performance[] {
  // The original seed migration used perf-* identifiers for demo performances.
  return rows
    .filter((row) => !row.kopis_performance_id?.startsWith("perf-"))
    .map((row) => {
      const parts = datePartsForKorea(row.starts_at);
      const venue = firstRelation(row.venues);

      return {
        artists: row.artists ?? [],
        bookingUrl: row.booking_url ?? "#",
        city: venue?.city ?? "",
        date: parts.date,
        endDate: row.ends_on ?? undefined,
        id: row.kopis_performance_id ?? row.title,
        posterUrl: row.poster_url ?? "/window.svg",
        priceRange: row.price_range ?? "",
        programImageUrls: row.program_image_urls ?? [],
        program: (row.program_items ?? [])
          .sort((a, b) => a.position - b.position)
          .map((item) => ({
            composerName: item.composer_name ?? "",
            displayTitle: item.display_title,
            source: {
              confidence: Number(item.confidence),
              label:
                item.source_provider === "nol"
                  ? "NOL 원문"
                  : (sourceLabels[item.source_type] ?? sourceLabels.unknown),
              type: item.source_type,
            },
            workSlug: firstRelation(item.works)?.slug ?? "",
          })),
        programSourceUrl: row.program_source_url,
        programStatus:
          row.program_status ??
          ((row.program_items?.length ?? 0) > 0 ? "confirmed" : "unknown"),
        sourceLabel: row.source_label ?? "",
        status: row.status,
        time: parts.time,
        title: row.title,
        venue: venue?.name ?? "",
      };
    });
}

export async function getComposerDirectory(): Promise<
  ComposerDirectoryEntry[]
> {
  if (!isSupabaseConfigured) return copyBaselineComposerDirectory();

  try {
    const supabase = createSupabaseClient();
    const rows: ComposerDirectoryRow[] = [];

    for (let offset = 0; ; offset += COMPOSER_PAGE_SIZE) {
      const result = await supabase
        .from("composers")
        .select("id, name, name_ko, period")
        .order("name_ko", { ascending: true, nullsFirst: false })
        .order("id", { ascending: true })
        .range(offset, offset + COMPOSER_PAGE_SIZE - 1);

      if (result.error) return copyBaselineComposerDirectory();

      const page = (result.data ?? []) as ComposerDirectoryRow[];
      rows.push(...page);
      if (page.length < COMPOSER_PAGE_SIZE) break;
    }

    return mergeComposerRows(rows);
  } catch {
    return copyBaselineComposerDirectory();
  }
}

async function readCatalogPages<T>(
  supabase: ReturnType<typeof createSupabaseClient>,
  table: "works" | "performances",
  columns: string,
  sortColumn: string,
): Promise<T[]> {
  const rows: T[] = [];
  for (let offset = 0; ; offset += 1000) {
    const result = await supabase
      .from(table)
      .select(columns)
      .order(sortColumn, { ascending: true })
      .order("id", { ascending: true })
      .range(offset, offset + 999);
    if (result.error) throw new Error(`Catalog query failed: ${table}`);
    const page = (result.data ?? []) as T[];
    rows.push(...page);
    if (page.length < 1000) return rows;
  }
}

export async function getCatalogSnapshot(): Promise<CatalogSnapshot> {
  if (!isSupabaseConfigured) return unavailableSnapshot();

  try {
    const supabase = createSupabaseClient();

    const [workRows, performanceRows] = await Promise.all([
      readCatalogPages<WorkRow>(
        supabase,
        "works",
        `
          slug,
          title,
          title_ko,
          catalogue,
          instrumentation,
          popularity_rank,
          composers(id, name, name_ko, period),
          work_aliases(alias)
        `,
        "popularity_rank",
      ),
      readCatalogPages<PerformanceRow>(
        supabase,
        "performances",
        `
          kopis_performance_id,
          title,
          starts_at,
          ends_on,
          status,
          artists,
          price_range,
          booking_url,
          poster_url,
          source_label,
          program_status,
          program_source_url,
          program_image_urls,
          venues(name, city),
          program_items(
            display_title,
            composer_name,
            source_type,
            confidence,
            position,
            source_provider,
            works(slug)
          )
        `,
        "starts_at",
      ),
    ]);

    const performances = mapPerformances(performanceRows);
    return {
      performances,
      reviewQueue: [],
      source: "supabase",
      works: mapWorks(workRows, performances),
    };
  } catch {
    return unavailableSnapshot();
  }
}

export async function getCatalogWorkBySlug(slug: string) {
  const catalog = await getCatalogSnapshot();
  return {
    catalog,
    performances: getUpcomingPerformancesFromList(catalog.performances).filter(
      (performance) =>
        performance.program.some((item) => item.workSlug === slug),
    ),
    work: catalog.works.find((item) => item.slug === slug) ?? null,
  };
}

export async function getCatalogPerformanceById(id: string) {
  const catalog = await getCatalogSnapshot();
  return {
    catalog,
    performance: catalog.performances.find((item) => item.id === id) ?? null,
  };
}
