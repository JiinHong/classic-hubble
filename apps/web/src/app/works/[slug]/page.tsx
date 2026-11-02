import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PerformanceCard } from "@/components/PerformanceCard";
import { WatchlistButton } from "@/components/WatchlistButton";
import { WorkRelations } from "@/components/WorkRelations";
import { getCatalogWorkBySlug } from "@/lib/catalog";

export const dynamic = "force-dynamic";

type WorkPageProps = {
  params: Promise<{ slug: string }>;
};

export default async function WorkPage({ params }: WorkPageProps) {
  const { slug } = await params;
  const { performances, pastPerformances, work } = await getCatalogWorkBySlug(slug);

  if (!work) {
    notFound();
  }

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
        <div>
          <div className="flex items-start gap-4">
            <div className="min-w-0">
              <p className="text-sm text-neutral-500">{work.composer.nameKo}</p>
              <h1 className="mt-3 break-words text-2xl font-medium leading-snug text-neutral-900 sm:text-3xl">
                {work.titleKo}
              </h1>
              <p className="mt-3 break-words text-base leading-7 text-neutral-500">
                {work.title} {work.catalogue}
              </p>
            </div>
          </div>

          <dl className="mt-6 flex flex-wrap gap-x-10 gap-y-4">
            <div>
              <dt className="text-xs font-black text-stone-500">편성</dt>
              <dd className="mt-1 text-sm font-bold text-stone-950">{work.instrumentation || "미확인"}</dd>
            </div>
            <div>
              <dt className="text-xs font-black text-stone-500">작품 정보 출처</dt>
              <dd className="mt-1 text-sm font-bold text-stone-950">
                {work.referenceUrl ? <a className="underline" href={work.referenceUrl} target="_blank" rel="noreferrer">{work.referenceUrl.startsWith("https://www.wikidata.org/") ? "Wikidata" : "원문 보기"}</a> : "자체 정리"}
              </dd>
            </div>
          </dl>
        </div>

        <aside className="mt-6">
          <WatchlistButton workSlug={work.slug} />
          <details className="mt-5 text-sm text-neutral-500">
          <summary className="w-fit py-1">검색 별칭</summary>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
            {work.aliases.map((alias) => (
              <span
                key={alias}
                className="text-xs text-neutral-500"
              >
                {alias}
              </span>
            ))}
          </div>
          </details>
        </aside>
      </section>

      <WorkRelations work={work} />

      {[
        { id: "upcoming", title: "예정 공연", items: performances, empty: "현재 확인된 예정 공연이 없습니다." },
        { id: "past", title: "과거·종료 공연", items: pastPerformances, empty: "연결된 과거·종료 공연이 없습니다." },
      ].map((group) => (
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
