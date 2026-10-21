"use client";

import {
  findWorksByQueryInList,
  getUpcomingPerformancesFromList,
  type Performance,
  type Work,
} from "@classic-hubble/shared";
import {
  ChevronDown,
  ListMusic,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { useMemo, useState } from "react";

import { PerformanceCard } from "./PerformanceCard";
import { WorkCard } from "./WorkCard";

const quickQueries = ["라흐 피협 2번", "운명", "신세계", "브바협"];
const batchSize = 24;

type SearchMode = "works" | "performances";

type SearchExperienceProps = {
  initialQuery?: string;
  performances: Performance[];
  works: Work[];
};

export function SearchExperience({
  initialQuery = "",
  performances,
  works,
}: SearchExperienceProps) {
  const [query, setQuery] = useState(initialQuery);
  const [mode, setMode] = useState<SearchMode>("works");
  const [city, setCity] = useState("전체");
  const [visibleCount, setVisibleCount] = useState(batchSize);

  function changeQuery(value: string) {
    setQuery(value);
    setVisibleCount(batchSize);
  }

  const workResults = useMemo(() => {
    const trimmed = query.trim();
    return trimmed ? findWorksByQueryInList(works, trimmed) : works;
  }, [query, works]);
  const matchedWorkSlugs = useMemo(
    () => new Set(workResults.map((work) => work.slug)),
    [workResults],
  );

  const performanceResults = useMemo(() => {
    const lowered = query.trim().toLowerCase();

    return getUpcomingPerformancesFromList(performances).filter(
      (performance) => {
        const cityMatches = city === "전체" || performance.city === city;
        if (!cityMatches) return false;
        if (!lowered) return true;

        const haystack = [
          performance.title,
          performance.venue,
          performance.city,
          ...performance.artists,
          ...performance.program.flatMap((item) => [
            item.composerName,
            item.displayTitle,
            item.source.label,
          ]),
        ]
          .join(" ")
          .toLowerCase();

        return (
          haystack.includes(lowered) ||
          performance.program.some((item) =>
            matchedWorkSlugs.has(item.workSlug),
          )
        );
      },
    );
  }, [city, matchedWorkSlugs, performances, query]);

  return (
    <section aria-labelledby="search-heading" className="space-y-5">
      <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 size-5 -translate-y-1/2 text-stone-400"
            />
            <label htmlFor="concert-search" className="sr-only">
              곡명, 작곡가, 공연장 검색
            </label>
            <input
              id="concert-search"
              value={query}
              onChange={(event) => changeQuery(event.target.value)}
              placeholder="곡명, 별칭, 작곡가, 공연장"
              className="h-12 w-full rounded-md border border-stone-300 bg-white pl-10 pr-3 text-base font-semibold text-stone-950 outline-none transition placeholder:text-stone-400 focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
            />
          </div>

          <div className="grid h-12 grid-cols-2 rounded-md border border-stone-200 bg-stone-100 p-1 lg:w-56">
            {(["works", "performances"] as const).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => {
                  setMode(item);
                  setVisibleCount(batchSize);
                }}
                aria-pressed={mode === item}
                className={`rounded-md text-sm font-black transition ${
                  mode === item
                    ? "bg-white text-stone-950 shadow-sm"
                    : "text-stone-500 hover:text-stone-950"
                }`}
              >
                {item === "works" ? "곡" : "공연"}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="inline-flex h-8 items-center gap-1 rounded-md bg-stone-100 px-2 text-xs font-bold text-stone-500">
            <ListMusic aria-hidden="true" className="size-3.5" />곡 바로 찾기
          </span>
          {quickQueries.map((quickQuery) => (
            <button
              key={quickQuery}
              type="button"
              onClick={() => changeQuery(quickQuery)}
              className="h-8 rounded-md border border-stone-200 px-3 text-sm font-semibold text-stone-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-800"
            >
              {quickQuery}
            </button>
          ))}
        </div>
      </div>

      {mode === "performances" ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex h-9 items-center gap-1 rounded-md bg-white px-3 text-sm font-bold text-stone-500 ring-1 ring-stone-200">
            <SlidersHorizontal aria-hidden="true" className="size-4" />
            지역
          </span>
          {["전체", "서울", "부천", "인천"].map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => {
                setCity(item);
                setVisibleCount(batchSize);
              }}
              aria-pressed={city === item}
              className={`h-9 rounded-md border px-3 text-sm font-bold transition ${
                city === item
                  ? "border-stone-950 bg-stone-950 text-white"
                  : "border-stone-200 bg-white text-stone-600 hover:border-stone-400"
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      ) : null}

      <div className="flex items-end justify-between gap-4">
        <div>
          <h1
            id="search-heading"
            className="text-2xl font-black tracking-normal text-stone-950"
          >
            {mode === "works" ? "곡으로 찾는 공연" : "예정 공연"}
          </h1>
          <p className="mt-1 text-sm font-semibold text-stone-500">
            {mode === "works"
              ? `${workResults.length}개 작품 매칭`
              : `${performanceResults.length}개 공연 매칭`}
          </p>
        </div>
      </div>

      {(mode === "works" ? workResults : performanceResults).length === 0 ? (
        <p role="status" className="py-12 text-center text-sm text-stone-500">
          검색 결과가 없습니다.
        </p>
      ) : mode === "works" ? (
        <div className="grid gap-4 md:grid-cols-2">
          {workResults.slice(0, visibleCount).map((work) => (
            <WorkCard key={work.slug} work={work} />
          ))}
          {visibleCount < workResults.length ? (
            <button
              type="button"
              onClick={() => setVisibleCount((count) => count + batchSize)}
              className="flex h-11 items-center justify-center gap-2 rounded-md border border-stone-300 bg-white text-sm font-bold text-stone-700 hover:bg-stone-50 md:col-span-2"
            >
              <ChevronDown aria-hidden="true" className="size-4" />
              작품 더 보기
            </button>
          ) : null}
        </div>
      ) : (
        <div className="grid gap-4">
          {performanceResults
            .slice(0, visibleCount)
            .map((performance, index) => (
              <PerformanceCard
                eager={index === 0}
                key={performance.id}
                performance={performance}
              />
            ))}
          {visibleCount < performanceResults.length ? (
            <button
              type="button"
              onClick={() => setVisibleCount((count) => count + batchSize)}
              className="flex h-11 items-center justify-center gap-2 rounded-md border border-stone-300 bg-white text-sm font-bold text-stone-700 hover:bg-stone-50"
            >
              <ChevronDown aria-hidden="true" className="size-4" />
              공연 더 보기
            </button>
          ) : null}
        </div>
      )}
    </section>
  );
}
