import { getUpcomingPerformancesFromList } from "@classic-hubble/shared";
import {
  BadgeAlert,
  BellRing,
  RadioTower,
  RefreshCw,
  ScanText,
  TrendingUp,
} from "lucide-react";

import { PerformanceCard } from "@/components/PerformanceCard";
import { SearchExperience } from "@/components/SearchExperience";
import { getCatalogSnapshot } from "@/lib/catalog";

export const dynamic = "force-dynamic";

type HomeProps = {
  searchParams: Promise<{ composer?: string | string[] }>;
};

export default async function Home({ searchParams }: HomeProps) {
  const composerParam = (await searchParams).composer;
  const initialComposerQuery =
    typeof composerParam === "string"
      ? composerParam
      : (composerParam?.[0] ?? "");
  const catalog = await getCatalogSnapshot();
  if (catalog.source === "unavailable") {
    return (
      <main className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div role="alert" className="space-y-3">
          <h1 className="text-xl font-bold">
            공연 정보를 불러오지 못했습니다.
          </h1>
          <p className="text-stone-600">잠시 후 다시 시도해 주세요.</p>
          <form action="/" method="get">
            <button
              type="submit"
              className="inline-flex items-center gap-2 font-semibold text-emerald-700"
            >
              <RefreshCw aria-hidden="true" className="size-4" />
              다시 불러오기
            </button>
          </form>
        </div>
      </main>
    );
  }
  const upcomingPerformances = getUpcomingPerformancesFromList(
    catalog.performances,
  );
  const confirmedCount = upcomingPerformances.filter(
    (performance) => performance.program.length > 0,
  ).length;

  return (
    <main>
      <section className="border-b border-stone-200 bg-white">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:px-8">
          <SearchExperience
            initialQuery={initialComposerQuery}
            performances={upcomingPerformances}
            works={catalog.works}
          />

          <aside className="space-y-4">
            <div className="rounded-lg border border-stone-200 bg-stone-950 p-5 text-white shadow-sm">
              <div className="flex items-center gap-2 text-sm font-bold text-emerald-200">
                <RadioTower aria-hidden="true" className="size-4" />
                등록된 공연
              </div>
              <dl className="mt-5 grid grid-cols-3 gap-3">
                <div>
                  <dt className="text-xs font-bold text-stone-400">작품</dt>
                  <dd className="mt-1 text-2xl font-black">
                    {catalog.works.length}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-bold text-stone-400">
                    예정 공연
                  </dt>
                  <dd className="mt-1 text-2xl font-black">
                    {upcomingPerformances.length}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-bold text-stone-400">
                    곡목 확인
                  </dt>
                  <dd className="mt-1 text-2xl font-black">{confirmedCount}</dd>
                </div>
              </dl>
            </div>

            <div className="rounded-lg border border-amber-200 bg-amber-50 p-5">
              <div className="flex items-start gap-3">
                <ScanText
                  aria-hidden="true"
                  className="mt-1 size-5 text-amber-700"
                />
                <div>
                  <h2 className="text-base font-black text-stone-950">
                    프로그램 확인 중
                  </h2>
                  <p className="mt-1 text-sm font-semibold text-stone-600">
                    아직 곡목을 확인하지 못한 예정 공연{" "}
                    {upcomingPerformances.length - confirmedCount}건
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2">
                <BellRing aria-hidden="true" className="size-5 text-rose-700" />
                <h2 className="text-base font-black text-stone-950">
                  가까운 공연
                </h2>
              </div>
              <div className="mt-4 space-y-3">
                {upcomingPerformances.slice(0, 3).map((performance) => (
                  <div
                    key={performance.id}
                    className="border-b border-stone-100 pb-3 last:border-b-0 last:pb-0"
                  >
                    <p className="line-clamp-1 text-sm font-black text-stone-950">
                      {performance.title}
                    </p>
                    <p className="mt-1 line-clamp-1 text-sm text-stone-500">
                      {performance.venue} · {performance.date}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-black text-emerald-700">
              <TrendingUp aria-hidden="true" className="size-4" />
              공연 일정
            </div>
            <h2 className="mt-1 text-2xl font-black tracking-normal text-stone-950">
              곧 열리는 주요 공연
            </h2>
          </div>
          <span className="inline-flex h-9 items-center gap-1 rounded-md bg-white px-3 text-sm font-bold text-stone-600 ring-1 ring-stone-200">
            <BadgeAlert aria-hidden="true" className="size-4 text-rose-700" />
            KOPIS 제공
          </span>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          {upcomingPerformances.slice(0, 4).map((performance, index) => (
            <PerformanceCard
              compact
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
