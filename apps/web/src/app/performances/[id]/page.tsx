import { ArrowLeft, CalendarDays, ExternalLink, MapPin, Ticket } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import {
  formatPerformanceDate,
  programPublicationMessage,
  performedScopeLabel,
  statusLabel,
  statusTone,
} from "@/lib/format";
import { getCatalogPerformanceById } from "@/lib/catalog";
import { posterImage } from "@/lib/poster";

export const dynamic = "force-dynamic";

type PerformancePageProps = {
  params: Promise<{ id: string }>;
};

export default async function PerformancePage({ params }: PerformancePageProps) {
  const { id } = await params;
  const { performance } = await getCatalogPerformanceById(id);

  if (!performance) {
    notFound();
  }

  const programStatus =
    performance.programStatus ??
    (performance.program.length > 0 ? "confirmed" : "unknown");

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <Link
        href="/"
        className="inline-flex h-10 items-center gap-2 rounded-md px-2 text-sm font-bold text-stone-600 hover:bg-stone-100 hover:text-stone-950"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        탐색으로
      </Link>

      <section className="mt-5 grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="relative aspect-[3/4] overflow-hidden rounded-lg border border-stone-200 bg-stone-100 shadow-sm">
          <Image
            {...posterImage(performance.posterUrl)}
            alt={`${performance.title} 포스터`}
            className="object-cover"
            fill
            priority
            sizes="(min-width: 1024px) 360px, 100vw"
          />
        </div>

        <div className="rounded-lg border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex h-7 items-center rounded-md border px-2 text-xs font-bold ${statusTone(
                performance.status,
              )}`}
            >
              {statusLabel(performance.status)}
            </span>
            <span className="rounded-md bg-stone-100 px-2 py-1 text-xs font-bold text-stone-600">
              {performance.sourceLabel}
            </span>
          </div>

          <h1 className="mt-4 text-3xl font-black tracking-normal text-stone-950">
            {performance.title}
          </h1>

          <dl className="mt-6 grid gap-3 text-sm font-semibold text-stone-600">
            <div className="flex items-center gap-2">
              <CalendarDays aria-hidden="true" className="size-4 text-emerald-700" />
              <dt className="sr-only">일시</dt>
              <dd>{formatPerformanceDate(performance)}</dd>
            </div>
            <div className="flex items-center gap-2">
              <MapPin aria-hidden="true" className="size-4 text-sky-700" />
              <dt className="sr-only">장소</dt>
              <dd>
                {performance.venue} · {performance.city}
              </dd>
            </div>
            <div className="flex items-center gap-2">
              <Ticket aria-hidden="true" className="size-4 text-rose-700" />
              <dt className="sr-only">가격</dt>
              <dd>{performance.priceRange}</dd>
            </div>
          </dl>

          <div className="mt-6">
            <h2 className="text-base font-black text-stone-950">출연</h2>
            <div className="mt-2 flex flex-wrap gap-2">
              {performance.artists.map((artist) => (
                <span
                  key={artist}
                  className="rounded-md border border-stone-200 bg-stone-50 px-2 py-1 text-sm font-semibold text-stone-600"
                >
                  {artist}
                </span>
              ))}
            </div>
          </div>

          <div className="mt-6">
            <h2 className="text-base font-black text-stone-950">프로그램</h2>
            <p className="mt-2 text-sm font-semibold text-stone-500">
              {programPublicationMessage(programStatus)}
            </p>
            <div className="mt-3 grid gap-3">
              {performance.program.map((item, index) => {
                const content = (
                  <>
                  <div className="flex flex-wrap items-center gap-2">
                    <ConfidenceBadge source={item.source} />
                    {item.performedScope ? (
                      <span className="text-sm font-semibold text-stone-600">
                        {performedScopeLabel(item.performedScope)}
                      </span>
                    ) : null}
                  </div>
                  {item.composerName ? (
                    <p className="mt-3 text-sm font-black text-stone-950">
                      {item.composerName}
                    </p>
                  ) : null}
                  <p className="mt-1 whitespace-pre-line text-base font-semibold text-stone-700">
                    {item.displayTitle}
                  </p>
                  {item.scopeDetails?.length ? (
                    <p className="mt-1 whitespace-pre-line text-sm text-stone-600">
                      {item.scopeDetails.join("\n")}
                    </p>
                  ) : null}
                  </>
                );
                const key = `${performance.id}-${index}-${item.displayTitle}`;

                return item.workSlug ? (
                  <Link
                    key={key}
                    href={`/works/${item.workSlug}`}
                    className="rounded-lg border border-stone-200 bg-stone-50 p-4 transition hover:border-emerald-300 hover:bg-emerald-50"
                  >
                    {content}
                  </Link>
                ) : (
                  <div
                    key={key}
                    className="rounded-lg border border-stone-200 bg-stone-50 p-4"
                  >
                    {content}
                  </div>
                );
              })}
              {performance.program.length === 0 && performance.programSourceUrl ? (
                <a
                  href={performance.programSourceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 text-sm font-bold text-emerald-800 hover:text-emerald-950"
                >
                  NOL 상세 정보 보기
                  <ExternalLink aria-hidden="true" className="size-4" />
                </a>
              ) : null}
            </div>
          </div>

          <a
            href={performance.bookingUrl}
            target="_blank"
            rel="noreferrer"
            className="mt-7 inline-flex h-12 items-center justify-center gap-2 rounded-md bg-stone-950 px-5 text-sm font-black text-white transition hover:bg-emerald-800"
          >
            예매처로 이동
            <ExternalLink aria-hidden="true" className="size-4" />
          </a>
        </div>
      </section>
    </main>
  );
}
