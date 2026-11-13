"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import {
  filterAndSortComposers,
  type ComposerDirectoryEntry,
  type ComposerPeriodKey,
} from "@/lib/composer-directory";

import { ComposerList } from "./ComposerList";
import { ComposerPeriodFilter } from "./ComposerPeriodFilter";

export function ComposerDirectory({
  composers,
}: {
  composers: ComposerDirectoryEntry[];
}) {
  const [period, setPeriod] = useState<"all" | ComposerPeriodKey>("all");
  const [query, setQuery] = useState("");

  const visibleComposers = useMemo(
    () => filterAndSortComposers(composers, { period, query, sort: "ko" }),
    [composers, period, query],
  );

  if (composers.length === 0) {
    return (
      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-black text-stone-950">작곡가</h1>
        <p className="mt-8 border-y border-stone-200 py-12 text-center text-sm font-bold text-stone-500">
          작곡가 데이터를 불러오지 못했습니다
        </p>
        <div className="mt-4 text-center">
          <Link
            className="text-sm font-black text-emerald-800 underline"
            href="/composers"
          >
            다시 시도
          </Link>
        </div>
      </section>
    );
  }

  return (
    <>
      <section className="border-b border-stone-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-7 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-black text-stone-950">작곡가</h1>
          <p aria-live="polite" className="mt-1 text-sm font-bold text-stone-500">
            {visibleComposers.length}명의 작곡가
          </p>

          <label
            className="mt-6 block text-sm font-black text-stone-800"
            htmlFor="composer-search"
          >
            작곡가 이름 검색
          </label>
          <div className="relative mt-2">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 size-5 -translate-y-1/2 text-stone-400"
            />
            <input
              className="h-12 w-full border border-stone-300 bg-white pl-10 pr-3 font-semibold text-stone-950 outline-none focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"
              id="composer-search"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="한글 또는 원어 이름"
              type="search"
              value={query}
            />
          </div>
        </div>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <ComposerPeriodFilter onChange={setPeriod} value={period} />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {visibleComposers.length ? (
          <ComposerList
            composers={visibleComposers}
            searching={Boolean(query.trim())}
          />
        ) : (
          <p className="border-y border-stone-200 py-14 text-center text-sm font-bold text-stone-500">
            조건에 맞는 작곡가가 없습니다
          </p>
        )}
      </section>
    </>
  );
}
