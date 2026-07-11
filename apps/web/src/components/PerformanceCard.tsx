import type { Performance } from "@classic-hubble/shared";
import { CalendarDays, MapPin, Ticket } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { compactArtists, formatPerformanceDate, statusLabel, statusTone } from "@/lib/format";

import { ConfidenceBadge } from "./ConfidenceBadge";

type PerformanceCardProps = {
  compact?: boolean;
  eager?: boolean;
  performance: Performance;
};

export function PerformanceCard({
  compact = false,
  eager = false,
  performance,
}: PerformanceCardProps) {
  const primaryProgram = performance.program[0];

  return (
    <article className="grid overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:border-stone-300 hover:shadow-md sm:grid-cols-[132px_minmax(0,1fr)]">
      <Link
        href={`/performances/${performance.id}`}
        className="relative block min-h-44 bg-stone-100 sm:min-h-full"
      >
        <Image
          src={performance.posterUrl}
          alt={`${performance.title} 포스터`}
          className="absolute inset-0 h-full w-full object-cover"
          fill
          loading={eager ? "eager" : "lazy"}
          sizes="(min-width: 640px) 132px, 100vw"
          unoptimized
        />
      </Link>

      <div className="flex min-w-0 flex-col gap-3 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex h-7 items-center rounded-md border px-2 text-xs font-bold ${statusTone(
              performance.status,
            )}`}
          >
            {statusLabel(performance.status)}
          </span>
          {primaryProgram ? <ConfidenceBadge source={primaryProgram.source} /> : null}
        </div>

        <div className="min-w-0">
          <Link
            href={`/performances/${performance.id}`}
            className="line-clamp-2 text-base font-black leading-6 text-stone-950 hover:text-emerald-700"
          >
            {performance.title}
          </Link>
          {primaryProgram ? (
            <p className="mt-1 line-clamp-1 text-sm font-semibold text-stone-600">
              {primaryProgram.composerName
                ? `${primaryProgram.composerName} · `
                : null}
              {primaryProgram.displayTitle}
            </p>
          ) : null}
        </div>

        <dl className="grid gap-2 text-sm text-stone-600">
          <div className="flex items-center gap-2">
            <CalendarDays aria-hidden="true" className="size-4 text-emerald-700" />
            <dt className="sr-only">일시</dt>
            <dd>{formatPerformanceDate(performance)}</dd>
          </div>
          <div className="flex items-center gap-2">
            <MapPin aria-hidden="true" className="size-4 text-sky-700" />
            <dt className="sr-only">장소</dt>
            <dd className="truncate">
              {performance.venue} · {performance.city}
            </dd>
          </div>
          {!compact ? (
            <div className="flex items-center gap-2">
              <Ticket aria-hidden="true" className="size-4 text-rose-700" />
              <dt className="sr-only">가격</dt>
              <dd className="truncate">{performance.priceRange}</dd>
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
