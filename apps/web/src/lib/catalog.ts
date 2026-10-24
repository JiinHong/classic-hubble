import {
  getUpcomingPerformancesFromList,
  type ConfidenceLevel,
  type Performance,
  type ProgramPublicationStatus,
  type ReviewItem,
  type Work,
} from "@classic-hubble/shared";
import { unstable_cache } from "next/cache";
import { promisify } from "node:util";
import { gzip, gunzip } from "node:zlib";

import openOpusComposers from "@/data/openopus-composers.json";
import workComponents from "@/data/work-components.json";
import { attachWorkComponents } from "./work-components";

import {
  composerIdentityKey,
  toComposerDirectoryEntry,
  type ComposerDirectoryEntry,
} from "./composer-directory";
import { createSupabaseClient, isSupabaseConfigured } from "./supabase/client";

type SourceType = "supabase" | "unavailable";

export type CatalogSnapshot = {
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

const WORK_COLUMNS = `slug, title, title_ko, catalogue, instrumentation,
  popularity_rank, composers(id, name, name_ko, period), work_aliases(alias)`;
const PERFORMANCE_COLUMNS = `kopis_performance_id, title, starts_at, ends_on,
  status, artists, price_range, booking_url, poster_url, source_label,
  program_status, program_source_url, program_image_urls, venues(name, city),
  program_items(display_title, composer_name, source_type, confidence,
    position, source_provider, works(slug))`;

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

const dateFormatter = new Intl.DateTimeFormat("en", {
  day: "2-digit",
  month: "2-digit",
  timeZone: "Asia/Seoul",
  year: "numeric",
});
const timeFormatter = new Intl.DateTimeFormat("ko-KR", {
  hour: "2-digit",
  hourCycle: "h23",
  minute: "2-digit",
  timeZone: "Asia/Seoul",
});

function datePartsForKorea(value: string) {
  const date = new Date(value);
  const dateParts = Object.fromEntries(
    dateFormatter.formatToParts(date).map((part) => [part.type, part.value]),
  );
  const datePart = `${dateParts.year}-${dateParts.month}-${dateParts.day}`;
  const timePart = timeFormatter.format(date);

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
      popularityRank: row.popularity_rank ?? null,
      referenceUrl: /^wikidata-q[1-9]\d*$/.test(row.slug)
        ? `https://www.wikidata.org/wiki/${row.slug.slice(9).toUpperCase()}`
        : undefined,
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
              confidence: ["codex_vision", "paddleocr"].includes(item.source_provider)
                ? null
                : Number(item.confidence),
              label:
                item.source_provider === "nol"
                  ? "NOL 원문"
                  : item.source_provider === "codex_vision"
                    ? "이미지 판독"
                    : item.source_provider === "paddleocr"
                      ? "OCR 근거 확인"
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
    return mergeComposerRows(await readComposerRows());
  } catch {
    return copyBaselineComposerDirectory();
  }
}

const readComposerRows = unstable_cache(
  async () => {
    const supabase = createSupabaseClient();
    const rows: ComposerDirectoryRow[] = [];

    for (let offset = 0; ; offset += COMPOSER_PAGE_SIZE) {
      const result = await supabase
        .from("composers")
        .select("id, name, name_ko, period")
        .order("name_ko", { ascending: true, nullsFirst: false })
        .order("id", { ascending: true })
        .range(offset, offset + COMPOSER_PAGE_SIZE - 1);

      if (result.error) throw new Error("Composer query failed");

      const page = (result.data ?? []) as ComposerDirectoryRow[];
      rows.push(...page);
      if (page.length < COMPOSER_PAGE_SIZE) break;
    }

    return rows;
  },
  ["public-composer-rows-v1", process.env.NEXT_PUBLIC_SUPABASE_URL ?? ""],
  { revalidate: 60 },
);

// Cache bounded public pages, not a multi-megabyte snapshot or authenticated data.
const readCatalogPage = unstable_cache(
  async (
    table: "works" | "performances",
    columns: string,
    sortColumn: string,
    offset: number,
  ) => {
    const result = await createSupabaseClient()
      .from(table)
      .select(columns)
      .order(sortColumn, { ascending: true })
      .order("id", { ascending: true })
      .range(offset, offset + 999);
    if (result.error) throw new Error(`Catalog query failed: ${table}`);
    return result.data ?? [];
  },
  ["public-catalog-page-v1", process.env.NEXT_PUBLIC_SUPABASE_URL ?? ""],
  { revalidate: 60 },
);

async function readCatalogPages<T>(
  table: "works" | "performances",
  columns: string,
  sortColumn: string,
): Promise<T[]> {
  const rows: T[] = [];
  async function readPage(offset: number): Promise<T[]> {
    return (await readCatalogPage(table, columns, sortColumn, offset)) as T[];
  }
  const first = await readPage(0);
  rows.push(...first);
  if (first.length < 1000) return rows;
  for (let offset = 1000; ; offset += 4000) {
    const pages = await Promise.all(
      Array.from({ length: 4 }, (_, index) => readPage(offset + index * 1000)),
    );
    for (const page of pages) {
      rows.push(...page);
      if (page.length < 1000) return rows;
    }
  }
}

let cachedCatalog: { expires: number; value: CatalogSnapshot } | undefined;
let pendingCatalog: Promise<CatalogSnapshot> | undefined;
const compress = promisify(gzip);
const decompress = promisify(gunzip);

// Separate compressed groups stay below cache limits without dozens of lookups.
const readSharedCatalog = unstable_cache(
  async (
    table: "works" | "performances",
    columns: string,
    sortColumn: string,
  ) => {
    const rows = await readCatalogPages(table, columns, sortColumn);
    const encoded = (await compress(JSON.stringify(rows))).toString("base64");
    // Leave room below the platform's per-entry limit; larger catalogs use pages.
    return encoded.length <= 1_800_000 ? encoded : null;
  },
  ["public-catalog-group-v1", process.env.NEXT_PUBLIC_SUPABASE_URL ?? ""],
  { revalidate: 60 },
);

async function readSharedCatalogRows<T>(
  table: "works" | "performances",
  columns: string,
  sortColumn: string,
): Promise<T[]> {
  const encoded = await readSharedCatalog(table, columns, sortColumn);
  if (encoded === null) return readCatalogPages<T>(table, columns, sortColumn);
  return JSON.parse(
    (await decompress(Buffer.from(encoded, "base64"))).toString("utf8"),
  );
}

// Only anonymous, public catalog data is shared; user libraries never enter this cache.
export async function getCatalogSnapshot(): Promise<CatalogSnapshot> {
  if (!isSupabaseConfigured) return unavailableSnapshot();
  if (cachedCatalog && cachedCatalog.expires > Date.now())
    return cachedCatalog.value;
  if (pendingCatalog) return pendingCatalog;
  pendingCatalog = readCatalogSnapshot()
    .then((value) => {
      if (value.source === "supabase")
        cachedCatalog = { expires: Date.now() + 60_000, value };
      return value;
    })
    .finally(() => {
      pendingCatalog = undefined;
    });
  return pendingCatalog;
}

async function readCatalogSnapshot(): Promise<CatalogSnapshot> {
  if (!isSupabaseConfigured) return unavailableSnapshot();

  try {
    const [workRows, performanceRows] = await Promise.all([
      readSharedCatalogRows<WorkRow>("works", WORK_COLUMNS, "popularity_rank"),
      readSharedCatalogRows<PerformanceRow>(
        "performances",
        PERFORMANCE_COLUMNS,
        "starts_at",
      ),
    ]);

    const performances = mapPerformances(performanceRows);
    return {
      performances,
      reviewQueue: [],
      source: "supabase",
      works: attachWorkComponents(
        mapWorks(workRows, performances),
        workComponents,
      ),
    };
  } catch {
    return unavailableSnapshot();
  }
}

export async function getCatalogWorkBySlug(slug: string) {
  const selection = await getCatalogSelection([slug], { includePast: true });
  const performances = getUpcomingPerformancesFromList(selection.performances);
  const upcomingIds = new Set(performances.map((performance) => performance.id));
  const pastPerformances = selection.performances
    .filter((performance) => !upcomingIds.has(performance.id))
    .sort(
      (a, b) =>
        (b.endDate ?? b.date).localeCompare(a.endDate ?? a.date) ||
        `${b.date} ${b.time}`.localeCompare(`${a.date} ${a.time}`),
    );
  return {
    performances,
    pastPerformances,
    work: selection.works[0] ?? null,
  };
}

export async function getCatalogPerformanceById(id: string) {
  const result = await createSupabaseClient()
    .from("performances")
    .select(PERFORMANCE_COLUMNS)
    .eq("kopis_performance_id", id)
    .maybeSingle();
  if (result.error) throw new Error("Performance query failed");
  return {
    performance:
      mapPerformances(
        result.data ? [result.data as unknown as PerformanceRow] : [],
      )[0] ?? null,
  };
}

const relatedWorks = new Map<string, Set<string>>();
for (const { parent_slug, child_slug } of workComponents) {
  for (const [from, to] of [
    [parent_slug, child_slug],
    [child_slug, parent_slug],
  ]) {
    const neighbors = relatedWorks.get(from) ?? new Set<string>();
    neighbors.add(to);
    relatedWorks.set(from, neighbors);
  }
}

export async function getCatalogSelection(
  slugs: string[],
  { includePast = false }: { includePast?: boolean } = {},
) {
  if (!slugs.length) return { works: [], performances: [] };
  const selected = new Set(slugs);
  const related = new Set(slugs);
  const pending = [...slugs];
  // Retain the connected family so relation validation (including cycles) stays intact.
  while (pending.length) {
    for (const slug of relatedWorks.get(pending.pop()!) ?? []) {
      if (related.has(slug)) continue;
      related.add(slug);
      pending.push(slug);
    }
  }
  const supabase = createSupabaseClient();
  const readWorks = async () => {
    const rows: WorkRow[] = [];
    const requested = [...related];
    for (let offset = 0; offset < requested.length; offset += 100) {
      const result = await supabase
        .from("works")
        .select(WORK_COLUMNS)
        .in("slug", requested.slice(offset, offset + 100));
      if (result.error) throw new Error("Work query failed");
      rows.push(...((result.data ?? []) as unknown as WorkRow[]));
    }
    return rows;
  };
  const readPerformances = async () => {
    const rows: PerformanceRow[] = [];
    for (let offset = 0; ; offset += 1000) {
      // Filter through a separate relation to keep the complete concert program.
      const result = await supabase
        .from("performances")
        .select(
          `${PERFORMANCE_COLUMNS}, matched:program_items!inner(works!inner(slug))`,
        )
        .in("matched.works.slug", [...selected])
        .order("starts_at", { ascending: true })
        .order("id", { ascending: true })
        .range(offset, offset + 999);
      if (result.error) throw new Error("Work performances query failed");
      const page = (result.data ?? []) as unknown as PerformanceRow[];
      rows.push(...page);
      if (page.length < 1000) break;
    }
    const performances = mapPerformances(rows);
    return includePast
      ? performances
      : getUpcomingPerformancesFromList(performances);
  };
  const [rows, performances] = await Promise.all([
    readWorks(),
    readPerformances(),
  ]);
  return {
    works: attachWorkComponents(
      mapWorks(rows, performances),
      workComponents,
    ).filter((work) => selected.has(work.slug)),
    performances,
  };
}
