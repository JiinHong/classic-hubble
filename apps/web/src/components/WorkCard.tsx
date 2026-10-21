import type { Work } from "@classic-hubble/shared";
import { ArrowUpRight, Music2 } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

type WorkCardProps = {
  action?: ReactNode;
  work: Work;
};

export function WorkCard({ action, work }: WorkCardProps) {
  const performanceCount = work.upcomingPerformanceIds.length;

  return (
    <article className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-stone-300 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div className="grid size-11 shrink-0 place-items-center rounded-md bg-emerald-50 text-emerald-800">
          <Music2 aria-hidden="true" className="size-5" />
        </div>
        {work.popularityRank !== null && (
          <span className="rounded-md bg-stone-100 px-2 py-1 text-xs font-bold text-stone-600">
            #{work.popularityRank}
          </span>
        )}
      </div>

      <div className="mt-4 min-w-0">
        <Link
          href={`/works/${work.slug}`}
          className="group inline-flex max-w-full items-start gap-1 text-lg font-black leading-6 text-stone-950 hover:text-emerald-700"
        >
          <span className="line-clamp-2">{work.composer.nameKo} · {work.titleKo}</span>
          <ArrowUpRight
            aria-hidden="true"
            className="mt-1 size-4 shrink-0 opacity-0 transition group-hover:opacity-100"
          />
        </Link>
        {work.partOf?.map((parent) => (
          <Link key={parent.slug} href={`/works/${parent.slug}`}
            className="mt-2 block break-words text-sm font-semibold leading-5 text-emerald-800 hover:underline">
            {parent.titleKo} · {parent.position === null ? "수록곡" : `${parent.position}번 수록곡`}
          </Link>
        ))}
        <p className="mt-1 line-clamp-1 text-sm font-semibold text-stone-600">
          {work.title} {work.catalogue}
        </p>
        <p className="mt-3 text-sm text-stone-500">{work.instrumentation}</p>
      </div>

      <div className="mt-4 flex items-center justify-between gap-3 border-t border-stone-100 pt-4 text-sm">
        <span className="font-bold text-stone-950">
          예정 공연 {performanceCount}건
        </span>
        {action}
      </div>
    </article>
  );
}
