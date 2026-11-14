import type { Work } from "@classic-hubble/shared";
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { workDisplay } from "@/lib/work-display";

export function WorkRelations({ work }: { work: Work }) {
  if (!work.partOf?.length && !work.parts?.length) return null;
  return (
    <section className="mt-8 space-y-8 border-y border-stone-200 py-6">
      {!!work.partOf?.length && <div>
        <h2 className="text-lg font-bold text-stone-950">수록 작품</h2>
        {work.partOf.map(parent => {
          const { heading, subtitle } = workDisplay(parent.title, parent.titleKo, parent.catalogue);
          return <Link key={parent.slug} href={`/works/${parent.slug}`}
          className="mt-3 flex items-center justify-between gap-3 py-2 font-semibold text-emerald-800 hover:underline">
          <span className="min-w-0 break-words">{heading}
            {parent.position !== null && ` · ${parent.position}번 수록곡`}
            {subtitle && <span className="mt-1 block text-sm font-normal text-stone-500">{subtitle}</span>}
          </span>
          <ChevronRight aria-hidden="true" className="size-4 shrink-0" />
        </Link>; })}
      </div>}
      {!!work.parts?.length && <div>
        <h2 className="text-lg font-bold text-stone-950">구성곡</h2>
        <ul className="mt-3 grid gap-x-8 divide-y divide-stone-100 sm:grid-cols-2">
          {work.parts.map(part => {
            const { heading, subtitle } = workDisplay(part.title, part.titleKo, part.catalogue);
            return <li key={part.slug}>
            <Link href={`/works/${part.slug}`} className="flex items-start gap-3 py-3 hover:text-emerald-800">
              <span className="w-8 shrink-0 pt-0.5 text-sm tabular-nums text-stone-500">{part.position ?? ""}</span>
              <span className="min-w-0 break-words font-semibold">{heading}
                {subtitle && <span className="mt-1 block text-sm font-normal text-stone-500">{subtitle}</span>}
              </span>
              <ChevronRight aria-hidden="true" className="ml-auto mt-1 size-4 shrink-0" />
            </Link>
          </li>; })}
        </ul>
      </div>}
    </section>
  );
}
