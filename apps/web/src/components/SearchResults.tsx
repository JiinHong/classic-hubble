"use client";

import { ArrowUpRight, ChevronDown, LoaderCircle, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { concertPeriod, type CatalogSearchResult, type ConcertPeriod } from "@/lib/catalog-search";
import type { SearchState } from "./SearchExperience";
import { WorkCard } from "./WorkCard";
import { PerformanceCard } from "./PerformanceCard";

type Props = { search: SearchState; offset: number; onMore: () => void; onMode: (mode: SearchState["mode"]) => void; onCity: (city: string) => void; onPeriod: (period: ConcertPeriod) => void };
const empty: CatalogSearchResult = { works: [], performances: [], total: 0, hasMore: false };

export function SearchResults({ search, offset, onMore, onMode, onCity, onPeriod }: Props) {
  const [retry, setRetry] = useState(0);
  const baseKey = JSON.stringify(search);
  const key = JSON.stringify([baseKey, offset, retry]);
  const [state, setState] = useState({ key: "", baseKey: "", result: empty, error: false });
  const cache = useRef(new Map<string, { expires: number; result: CatalogSearchResult }>());
  const loading = state.key !== key;
  const result = state.result;
  const { query, work, mode, city, period } = search;

  useEffect(() => {
    const controller = new AbortController();
    const cacheKey = JSON.stringify([baseKey, offset]);
    const cached = cache.current.get(cacheKey);
    const fresh = cached && cached.expires > Date.now();
    const load = async () => {
      try {
        let page: CatalogSearchResult;
        if (fresh) page = cached.result;
        else {
          const params = new URLSearchParams(work ? { work } : { q: query, mode });
          params.set("offset", String(offset));
          if (work || mode === "performances") { params.set("city", city); params.set("period", period); }
          const response = await fetch(`/api/catalog/${work ? "selected-work" : "search"}?${params}`, { signal: controller.signal });
          if (!response.ok) throw new Error("Search unavailable");
          page = await response.json();
        }
        if (controller.signal.aborted) return;
        if (!fresh) {
          cache.current.delete(cacheKey);
          cache.current.set(cacheKey, { expires: Date.now() + 60_000, result: page });
          if (cache.current.size > 20) cache.current.delete(cache.current.keys().next().value!);
        }
        setState(previous => ({ key, baseKey, error: false, result: offset && previous.baseKey === baseKey ? {
          ...page,
          works: [...new Map([...previous.result.works, ...page.works].map(w => [w.slug, w])).values()],
          performances: [...new Map([...previous.result.performances, ...page.performances].map(p => [p.id, p])).values()],
          matchedWorkSlugs: { ...previous.result.matchedWorkSlugs, ...page.matchedWorkSlugs },
        } : page }));
      } catch {
        if (!controller.signal.aborted) setState(previous => ({ ...previous, key, error: true }));
      }
    };
    void load();
    return () => controller.abort();
  }, [key, baseKey, offset, query, work, mode, city, period]);

  const showPerformances = !!work || mode === "performances";
  const noResults = showPerformances ? !result.performances.length : !result.works.length;
  const counts = result.periodCounts ?? { upcoming: result.performances.length, past: 0 };
  const split = period === "past" ? 0 : counts.upcoming;
  return (
    <section className="mt-10" aria-label="검색 결과" aria-busy={loading}>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <h1 className="min-w-0 break-words text-xl font-medium text-neutral-900 sm:text-2xl">{query || "선택한 작품"}</h1>
        {!work ? <div className="flex items-center gap-5" aria-label="검색 범위">
          {(["works", "performances"] as const).map(item => <button key={item} type="button" aria-pressed={mode === item} onClick={() => onMode(item)}
            className={`border-b-2 pb-2 text-sm ${mode === item ? "border-neutral-900 font-semibold text-neutral-900" : "border-transparent text-neutral-500 hover:text-neutral-900"}`}>{item === "works" ? "작품" : "공연"}</button>)}
        </div> : null}
      </div>
      {showPerformances ? <div className="mb-5 flex flex-wrap gap-x-5 gap-y-2 text-sm text-neutral-500">
        <label className="flex items-center gap-2">기간
          <select value={period} onChange={e => onPeriod(concertPeriod(e.target.value))} className="rounded-md border border-neutral-200 bg-white px-3 py-2 text-neutral-800">
            <option value="all">전체</option><option value="upcoming">예정 공연</option><option value="past">과거 공연</option>
          </select>
        </label><label className="flex items-center gap-2">지역
        <select value={city} onChange={e => onCity(e.target.value)} className="rounded-md border border-neutral-200 bg-white px-3 py-2 text-neutral-800">
          {[...new Set(["전체", ...(result.cities ?? []), city])].map(value => <option key={value}>{value}</option>)}
        </select>
      </label></div> : null}
      {!loading && state.error ? <div role="alert" className="py-14 text-sm text-neutral-600">검색 결과를 불러오지 못했습니다.
        <button type="button" onClick={() => setRetry(v => v + 1)} className="mt-4 flex items-center gap-2 text-neutral-900"><RotateCcw className="size-4" aria-hidden="true" />다시 시도</button>
      </div> : loading && offset === 0 ? <p role="status" className="flex items-center gap-2 py-14 text-sm text-neutral-500"><LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />검색 중입니다.</p> : <>
        {work && result.works[0] ? <div className="mb-6 border-b border-neutral-200 pb-6">
          <p className="mb-3 text-sm text-neutral-500">{result.works[0].composer.nameKo}</p>
          <Link className="inline-flex items-center gap-1 text-sm text-emerald-800 hover:underline" href={`/works/${work}`}>작품과 과거 공연<ArrowUpRight className="size-4" aria-hidden="true" /></Link>
        </div> : null}
        {noResults ? <p role="status" className="py-12 text-sm text-neutral-500">{showPerformances && period !== "all" ? `조건에 맞는 ${period === "past" ? "과거" : "예정"} 공연이 없습니다.` : "검색 결과가 없습니다."}</p> :
          showPerformances ? (["upcoming","past"] as const).map(group => {
            if (period !== "all" && period !== group) return null;
            const items = group === "upcoming" ? result.performances.slice(0,split) : result.performances.slice(split);
            if (!items.length && counts[group]) return null;
            return <section key={group} className="mb-7" aria-labelledby={`concert-heading-${group}`}>
              <h2 id={`concert-heading-${group}`} className="text-base font-medium">{group === "past" ? "과거 공연" : "예정 공연"} <span className="text-sm text-neutral-500">{counts[group]}개</span></h2>
              <div className="divide-y divide-neutral-100">{items.map((p,i) => <PerformanceCard key={p.id} performance={p} eager={i === 0}
                showYear past={group === "past"} workSlug={work || result.matchedWorkSlugs?.[p.id]}
                metadataMatch={!!query && !work && !result.matchedWorkSlugs?.[p.id]} />)}</div>
            </section>;
          }) : <div className="divide-y divide-neutral-100">{result.works.map(w => <WorkCard key={w.slug} work={w} />)}</div>}
        {result.hasMore ? <button type="button" disabled={loading} onClick={onMore} className="mx-auto mt-7 flex h-11 items-center gap-2 px-4 text-sm text-neutral-600 hover:text-neutral-900 disabled:opacity-50">
          {loading ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <ChevronDown className="size-4" aria-hidden="true" />}{showPerformances ? "공연 더 보기" : "작품 더 보기"}
        </button> : null}
      </>}
    </section>
  );
}
