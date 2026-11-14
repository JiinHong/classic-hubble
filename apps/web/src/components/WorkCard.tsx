import type { Work } from "@classic-hubble/shared";
import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { workDisplay } from "@/lib/work-display";

type WorkCardProps = {
  action?: ReactNode;
  work: Work;
};

export function WorkCard({ action, work }: WorkCardProps) {
  const performanceCount = work.upcomingPerformanceIds.length;
  const { heading, subtitle } = workDisplay(work.title, work.titleKo, work.catalogue, work.composer.nameKo, work.composer.name);

  return (
    <article className="flex flex-col gap-3 py-6 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
      <div className="min-w-0">
        <Link
          href={`/works/${work.slug}`}
          className="group inline-flex max-w-full items-start gap-2 text-base font-medium leading-7 text-neutral-900 hover:text-emerald-800"
        >
          <span className="break-words">{work.composer.nameKo} · {heading}</span>
          <ArrowUpRight
            aria-hidden="true"
            className="mt-1.5 size-4 shrink-0 text-neutral-400"
          />
        </Link>
        {work.partOf?.map((parent) => (
          <Link key={parent.slug} href={`/works/${parent.slug}`}
            className="mt-2 block break-words text-sm font-semibold leading-5 text-emerald-800 hover:underline">
            {workDisplay(parent.title, parent.titleKo, parent.catalogue).heading} · {parent.position === null ? "수록곡" : `${parent.position}번 수록곡`}
          </Link>
        ))}
        {subtitle && <p className="mt-1 break-words text-sm leading-6 text-neutral-500">{subtitle}</p>}
      </div>

      <div className="flex shrink-0 items-center gap-3 pt-1 text-xs text-neutral-500 sm:flex-col sm:items-end">
        <span>
          예정 공연 {performanceCount}건
        </span>
        {action}
      </div>
    </article>
  );
}
