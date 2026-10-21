"use client";

import {
  SEARCH_PAGE_SIZE,
  type CatalogSearchResult,
  type SearchMode,
} from "@/lib/catalog-search";
import {
  ChevronDown,
  ListMusic,
  Search,
  SlidersHorizontal,
  Youtube,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { PerformanceCard } from "./PerformanceCard";
import { WorkCard } from "./WorkCard";

const quickQueries = ["라흐 피협 2번", "운명", "신세계", "브바협"];

type SearchExperienceProps = {
  initialQuery?: string;
  initialResult: CatalogSearchResult;
};

export function SearchExperience({
  initialQuery = "",
  initialResult,
}: SearchExperienceProps) {
  const [query, setQuery] = useState(initialQuery);
  const [mode, setMode] = useState<SearchMode>("works");
  const [city, setCity] = useState("전체");
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  const requestKey = JSON.stringify([query, mode, city, offset, retry]);
  const [state, setState] = useState({
    key: requestKey,
    result: initialResult,
    error: false,
  });
  const completedKey = useRef(requestKey);
  const recentResults = useRef(
    new Map<string, { expires: number; result: CatalogSearchResult }>(),
  );
  const loading = state.key !== requestKey;
  const error = !loading && state.error;
  const { works: workResults, performances: performanceResults } = state.result;

  useEffect(() => {
    if (completedKey.current === requestKey) return;
    const controller = new AbortController();
    const cacheKey = JSON.stringify([query.trim(), mode, city, offset]);
    const cached = recentResults.current.get(cacheKey);
    const fresh = cached && cached.expires > Date.now();
    const timer = setTimeout(
      async () => {
        try {
          const params = new URLSearchParams({
            q: query,
            mode,
            city,
            offset: String(offset),
          });
          let result: CatalogSearchResult;
          if (fresh) {
            result = cached.result;
          } else {
            const response = await fetch(`/api/catalog/search?${params}`, {
              signal: controller.signal,
            });
            if (!response.ok) throw new Error("Search unavailable");
            result = await response.json();
          }
          if (controller.signal.aborted) return;
          if (!fresh) {
            recentResults.current.delete(cacheKey);
            recentResults.current.set(cacheKey, {
              expires: Date.now() + 60_000,
              result,
            });
            if (recentResults.current.size > 20)
              recentResults.current.delete(
                recentResults.current.keys().next().value!,
              );
          }
          completedKey.current = requestKey;
          setState((previous) => ({
            key: requestKey,
            error: false,
            result:
              offset === 0
                ? result
                : {
                    ...result,
                    works: [...previous.result.works, ...result.works],
                    performances: [
                      ...previous.result.performances,
                      ...result.performances,
                    ],
                  },
          }));
        } catch {
          if (!controller.signal.aborted) {
            completedKey.current = requestKey;
            setState((previous) => ({
              ...previous,
              key: requestKey,
              error: true,
            }));
          }
        }
      },
      fresh ? 0 : 200,
    );
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, mode, city, offset, retry, requestKey]);

  function changeQuery(value: string) {
    setQuery(value);
    setOffset(0);
  }

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
              maxLength={200}
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
                  setOffset(0);
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
          <Link
            href="/youtube"
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-stone-200 px-3 text-sm font-semibold text-stone-700 hover:border-red-300 hover:bg-red-50"
          >
            <Youtube aria-hidden="true" className="size-4 text-red-600" />
            유튜브로 찾기
          </Link>
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
                setOffset(0);
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
            {loading
              ? "검색 중"
              : error
                ? "검색 일시 중단"
                : `${state.result.total}개 ${mode === "works" ? "작품" : "공연"} 매칭`}
          </p>
        </div>
      </div>

      {error ? (
        <div role="alert" className="py-8 text-sm text-stone-600">
          검색 결과를 불러오지 못했습니다.
          <button
            type="button"
            onClick={() => setRetry((value) => value + 1)}
            className="ml-3 font-bold text-emerald-800"
          >
            다시 시도
          </button>
        </div>
      ) : loading && offset === 0 ? (
        <p role="status" className="py-12 text-center text-sm text-stone-500">
          검색 중입니다.
        </p>
      ) : (mode === "works" ? workResults : performanceResults).length === 0 ? (
        <p role="status" className="py-12 text-center text-sm text-stone-500">
          검색 결과가 없습니다.
        </p>
      ) : mode === "works" ? (
        <div className="grid gap-4 md:grid-cols-2">
          {workResults.map((work) => (
            <WorkCard key={work.slug} work={work} />
          ))}
          {state.result.hasMore ? (
            <button
              type="button"
              disabled={loading}
              onClick={() => setOffset((count) => count + SEARCH_PAGE_SIZE)}
              className="flex h-11 items-center justify-center gap-2 rounded-md border border-stone-300 bg-white text-sm font-bold text-stone-700 hover:bg-stone-50 md:col-span-2"
            >
              <ChevronDown aria-hidden="true" className="size-4" />
              작품 더 보기
            </button>
          ) : null}
        </div>
      ) : (
        <div className="grid gap-4">
          {performanceResults.map((performance, index) => (
            <PerformanceCard
              eager={index === 0}
              key={performance.id}
              performance={performance}
            />
          ))}
          {state.result.hasMore ? (
            <button
              type="button"
              disabled={loading}
              onClick={() => setOffset((count) => count + SEARCH_PAGE_SIZE)}
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
