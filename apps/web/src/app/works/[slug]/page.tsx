import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PerformanceCard } from "@/components/PerformanceCard";
import { WatchlistButton } from "@/components/WatchlistButton";
import { WorkRelations } from "@/components/WorkRelations";
import { getCatalogWorkBySlug } from "@/lib/catalog";
import { workDisplay } from "@/lib/work-display";

export const dynamic = "force-dynamic";

type WorkPageProps = {
  params: Promise<{ slug: string }>;
};

export default async function WorkPage({ params }: WorkPageProps) {
  const { slug } = await params;
  const { performances, pastPerformances, cancelledPerformances, unavailablePerformances, work } = await getCatalogWorkBySlug(slug);

  if (!work) {
    notFound();
  }
  const { heading, subtitle } = workDisplay(work.title, work.titleKo, work.catalogue);

  return (
    <main className="mx-auto max-w-4xl px-4 pb-16 pt-6 sm:px-8">
      <Link
        href="/"
        className="inline-flex h-10 items-center gap-2 rounded-md px-2 text-sm font-bold text-stone-600 hover:bg-stone-100 hover:text-stone-950"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        검색으로
      </Link>

      <section className="mt-8 border-b border-neutral-200 pb-8">
        <p className="text-sm text-neutral-500">{work.composer.nameKo}</p>
        <h1 className="mt-2 break-words text-2xl font-medium leading-snug text-neutral-900 sm:text-3xl">
          {heading}
        </h1>
        {subtitle && <p className="mt-2 break-words text-base leading-7 text-neutral-500">{subtitle}</p>}
        <div className="mt-5">
          <WatchlistButton workSlug={work.slug} />
        </div>
      </section>

      <WorkRelations work={work} />

      {[
        { id: "upcoming", title: "예정 공연", items: performances, empty: "현재 확인된 예정 공연이 없습니다." },
        { id: "past", title: "지난 공연", items: pastPerformances, empty: "아직 지난 공연이 없습니다." },
        { id: "cancelled", title: "취소된 공연", items: cancelledPerformances },
        { id: "unavailable", title: "일정 확인 필요", items: unavailablePerformances },
      ].filter(group => group.empty || group.items.length).map((group) => (
        <section aria-labelledby={`${group.id}-heading`} className="mt-8" key={group.id}>
          <div className="mb-4">
            <div className="flex flex-wrap items-baseline gap-2">
              <h2 id={`${group.id}-heading`} className="text-lg font-medium text-neutral-900">{group.title}</h2>
              <span className="text-sm font-semibold tabular-nums text-stone-500">{group.items.length}건</span>
            </div>
            {!group.items.length && <p className="mt-2 text-sm text-stone-500">{group.empty}</p>}
          </div>
          <div className="divide-y divide-neutral-100">
            {group.items.map((performance, index) => (
              <PerformanceCard
                eager={index === 0 && (group.id === "upcoming" || !performances.length)}
                key={performance.id}
                performance={performance}
                workSlug={work.slug}
                showYear
              />
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
