import { ArrowLeft, Music2 } from "lucide-react";
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
  const { performances, work } = await getCatalogWorkBySlug(slug);

  if (!work) {
    notFound();
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <Link
        href="/"
        className="inline-flex h-10 items-center gap-2 rounded-md px-2 text-sm font-bold text-stone-600 hover:bg-stone-100 hover:text-stone-950"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        탐색으로
      </Link>

      <section className="mt-5 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="rounded-lg border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="grid size-12 shrink-0 place-items-center rounded-md bg-emerald-50 text-emerald-800">
              <Music2 aria-hidden="true" className="size-6" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-black text-emerald-700">{work.composer.nameKo}</p>
              <h1 className="mt-1 text-3xl font-black tracking-normal text-stone-950">
                {work.titleKo}
              </h1>
              <p className="mt-2 text-lg font-semibold text-stone-600">
                {work.title} {work.catalogue}
              </p>
            </div>
          </div>

          <dl className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg bg-stone-50 p-4">
              <dt className="text-xs font-black text-stone-500">편성</dt>
              <dd className="mt-1 text-sm font-bold text-stone-950">{work.instrumentation || "미확인"}</dd>
            </div>
            <div className="rounded-lg bg-stone-50 p-4">
              <dt className="text-xs font-black text-stone-500">작품 정보 출처</dt>
              <dd className="mt-1 text-sm font-bold text-stone-950">
                {work.referenceUrl ? <a className="underline" href={work.referenceUrl} target="_blank" rel="noreferrer">{work.referenceUrl.startsWith("https://www.wikidata.org/") ? "Wikidata" : "원문 보기"}</a> : "자체 정리"}
              </dd>
            </div>
            <div className="rounded-lg bg-stone-50 p-4">
              <dt className="text-xs font-black text-stone-500">예정 공연</dt>
              <dd className="mt-1 text-sm font-bold text-stone-950">{performances.length}건</dd>
            </div>
          </dl>
        </div>

        <aside className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <WatchlistButton workSlug={work.slug} />
          <h2 className="mt-6 text-sm font-black text-stone-950">검색 별칭</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {work.aliases.map((alias) => (
              <span
                key={alias}
                className="rounded-md border border-stone-200 bg-stone-50 px-2 py-1 text-xs font-semibold text-stone-600"
              >
                {alias}
              </span>
            ))}
          </div>
        </aside>
      </section>

      <WorkRelations work={work} />

      <section className="mt-8">
        <div className="mb-4">
          <h2 className="text-2xl font-black tracking-normal text-stone-950">예정 공연</h2>
          {!performances.length && <p className="mt-2 text-sm text-stone-500">현재 확인된 예정 공연이 없습니다.</p>}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {performances.map((performance, index) => (
            <PerformanceCard
              eager={index === 0}
              key={performance.id}
              performance={performance}
            />
          ))}
        </div>
      </section>
    </main>
  );
}
