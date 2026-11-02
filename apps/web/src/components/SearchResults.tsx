"use client";

import { ArrowUpRight, ChevronDown, LoaderCircle, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { CatalogSearchResult } from "@/lib/catalog-search";
import type { SearchState } from "./SearchExperience";
import { WorkCard } from "./WorkCard";
import { PerformanceCard } from "./PerformanceCard";

type Props = { search: SearchState; offset: number; onMore: () => void; onMode: (mode: SearchState["mode"]) => void; onCity: (city: string) => void };
const empty: CatalogSearchResult = { works: [], performances: [], total: 0, hasMore: false };

export function SearchResults({ search, offset, onMore, onMode, onCity }: Props) {
  const [retry, setRetry] = useState(0);
  const baseKey = JSON.stringify(search);
  const key = JSON.stringify([baseKey, offset, retry]);
  const [state, setState] = useState({ key: "", baseKey: "", result: empty, error: false });
  const cache = useRef(new Map<string, { expires: number; result: CatalogSearchResult }>());
  const loading = state.key !== key;
  const result = state.result;
  const { query, work, mode, city } = search;

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
          const params = work ? new URLSearchParams({ work, offset: String(offset) }) : new URLSearchParams({ q: query, mode, city, offset: String(offset) });
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
        } : page }));
      } catch {
        if (!controller.signal.aborted) setState(previous => ({ ...previous, key, error: true }));
      }
    };
    void load();
    return () => controller.abort();
  }, [key, baseKey, offset, query, work, mode, city]);

  const showPerformances = !!work || mode === "performances";
  const noResults = showPerformances ? !result.performances.length : !result.works.length;
  return (
    <section className="mt-10" aria-label="검색 결과" aria-busy={loading}>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <h1 className="min-w-0 break-words text-xl font-medium text-neutral-900 sm:text-2xl">{query || "선택한 작품"}</h1>
        {!work ? <div className="flex items-center gap-5" aria-label="검색 범위">
          {(["works", "performances"] as const).map(item => <button key={item} type="button" aria-pressed={mode === item} onClick={() => onMode(item)}
            className={`border-b-2 pb-2 text-sm ${mode === item ? "border-neutral-900 font-semibold text-neutral-900" : "border-transparent text-neutral-500 hover:text-neutral-900"}`}>{item === "works" ? "작품" : "공연"}</button>)}
        </div> : null}
      </div>
      {!work && mode === "performances" ? <label className="mb-5 flex items-center gap-3 text-sm text-neutral-500">지역
        <select value={city} onChange={e => onCity(e.target.value)} className="rounded-md border border-neutral-200 bg-white px-3 py-2 text-neutral-800">
          {[...new Set(["전체", "서울", "부천", "인천", city])].map(value => <option key={value}>{value}</option>)}
        </select>
      </label> : null}
      {!loading && state.error ? <div role="alert" className="py-14 text-sm text-neutral-600">검색 결과를 불러오지 못했습니다.
        <button type="button" onClick={() => setRetry(v => v + 1)} className="mt-4 flex items-center gap-2 text-neutral-900"><RotateCcw className="size-4" aria-hidden="true" />다시 시도</button>
      </div> : loading && offset === 0 ? <p role="status" className="flex items-center gap-2 py-14 text-sm text-neutral-500"><LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />검색 중입니다.</p> : <>
        {work && result.works[0] ? <div className="mb-6 border-b border-neutral-200 pb-6">
          <p className="mb-3 text-sm text-neutral-500">{result.works[0].composer.nameKo}</p>
          <Link className="inline-flex items-center gap-1 text-sm text-emerald-800 hover:underline" href={`/works/${work}`}>작품과 과거 공연<ArrowUpRight className="size-4" aria-hidden="true" /></Link>
          <h2 className="mt-7 text-base font-medium">예정 공연</h2>
        </div> : null}
        {noResults ? <p role="status" className="py-12 text-sm text-neutral-500">{work ? "현재 확인된 예정 공연이 없습니다." : "검색 결과가 없습니다."}</p> : <div className="divide-y divide-neutral-100">
          {showPerformances ? result.performances.map((p, i) => <PerformanceCard key={p.id} performance={p} eager={i === 0} workSlug={work || undefined} />) : result.works.map(w => <WorkCard key={w.slug} work={w} />)}
        </div>}
        {result.hasMore ? <button type="button" disabled={loading} onClick={onMore} className="mx-auto mt-7 flex h-11 items-center gap-2 px-4 text-sm text-neutral-600 hover:text-neutral-900 disabled:opacity-50">
          {loading ? <LoaderCircle className="size-4 animate-spin" aria-hidden="true" /> : <ChevronDown className="size-4" aria-hidden="true" />}{showPerformances ? "공연 더 보기" : "작품 더 보기"}
        </button> : null}
      </>}
    </section>
  );
}
