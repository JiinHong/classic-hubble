import type { Performance } from "@classic-hubble/shared";
import { CalendarDays, MapPin, Ticket } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { compactArtists, formatPerformanceDate, performedScopeLabel, performanceBadge } from "@/lib/format";
import { posterImage } from "@/lib/poster";

type PerformanceCardProps = {
  compact?: boolean;
  eager?: boolean;
  showYear?: boolean;
  workSlug?: string;
  metadataMatch?: boolean;
  performance: Performance;
};

export function PerformanceCard({
  compact = false,
  eager = false,
  showYear = false,
  workSlug,
  metadataMatch = false,
  performance,
}: PerformanceCardProps) {
  const badge = performanceBadge(performance);
  const primaryProgram = metadataMatch ? undefined : workSlug === undefined
    ? performance.program[0]
    : performance.program.find((item) => item.workSlug === workSlug);

  return (
    <article className="grid grid-cols-[72px_minmax(0,1fr)] items-start gap-4 py-6 sm:grid-cols-[100px_minmax(0,1fr)] sm:gap-6">
      <Link
        href={`/performances/${performance.id}`}
        className="relative block aspect-[3/4] overflow-hidden rounded bg-neutral-50"
      >
        <Image
          {...posterImage(performance.posterUrl)}
          alt={`${performance.title} 포스터`}
          className="absolute inset-0 h-full w-full object-contain"
          fill
          loading={eager ? "eager" : "lazy"}
          sizes="(min-width: 640px) 100px, 72px"
        />
      </Link>

      <div className="flex min-w-0 flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${badge.tone}`}
          >
            {badge.label}
          </span>
        </div>

        <div className="min-w-0">
          <Link
            href={`/performances/${performance.id}`}
            className="break-words text-base font-medium leading-6 text-neutral-900 hover:text-emerald-800"
          >
            {performance.title}
          </Link>
          {primaryProgram ? (
            <p className="mt-1 break-words text-sm leading-6 text-neutral-500">
              {primaryProgram.composerName
                ? `${primaryProgram.composerName} · `
                : null}
              {primaryProgram.displayTitle}
              {primaryProgram.performedScope ? ` · ${performedScopeLabel(primaryProgram.performedScope)}` : ""}
            </p>
          ) : null}
        </div>

        <dl className="grid gap-2 text-sm text-stone-600">
          <div className="flex items-center gap-2">
            <CalendarDays aria-hidden="true" className="size-4 text-emerald-700" />
            <dt className="sr-only">일시</dt>
            <dd>{formatPerformanceDate(performance, showYear)}</dd>
          </div>
          <div className="flex items-center gap-2">
            <MapPin aria-hidden="true" className="size-4 text-sky-700" />
            <dt className="sr-only">장소</dt>
            <dd className="min-w-0 break-words">
              {performance.venue} · {performance.city}
            </dd>
          </div>
          {!compact ? (
            <div className="flex items-center gap-2">
              <Ticket aria-hidden="true" className="size-4 text-rose-700" />
              <dt className="sr-only">가격</dt>
              <dd className="min-w-0 break-words">{performance.priceRange}</dd>
            </div>
          ) : null}
        </dl>

        {!compact ? (
          <p className="line-clamp-1 text-sm text-stone-500">
            {compactArtists(performance.artists)}
          </p>
        ) : null}
      </div>
    </article>
  );
}
