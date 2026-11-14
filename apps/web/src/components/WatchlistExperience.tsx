"use client";

import type { Performance, Work } from "@classic-hubble/shared";
import {
  Bell,
  BellOff,
  LoaderCircle,
  LogIn,
  Search,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "./AuthProvider";
import { PerformanceCard } from "./PerformanceCard";
import { useUserLibrary } from "./UserLibraryProvider";
import { WorkCard } from "./WorkCard";
import { workDisplay } from "@/lib/work-display";

export function WatchlistExperience() {
  const { loading: authLoading, signIn, user } = useAuth();
  const {
    error,
    isPending,
    loading: libraryLoading,
    toggleWork,
    watchedSlugs,
  } = useUserLibrary();

  const [retry, setRetry] = useState(0);
  const selectionKey = JSON.stringify([user?.id, watchedSlugs, retry]);
  const [selection, setSelection] = useState<{
    key: string;
    works: Work[];
    performances: Performance[];
    error: boolean;
  }>({ key: "", works: [], performances: [], error: false });
  const hasSelection = Boolean(user && !libraryLoading && watchedSlugs.length);
  useEffect(() => {
    if (!hasSelection) return;
    const controller = new AbortController();
    const slugs: string[] = JSON.parse(selectionKey)[1];
    void (async () => {
      try {
        const works: Work[] = [],
          performances = new Map<string, Performance>();
        for (let offset = 0; offset < slugs.length; offset += 100) {
          const params = new URLSearchParams(
            slugs.slice(offset, offset + 100).map((slug) => ["slug", slug]),
          );
          const response = await fetch(`/api/catalog/selection?${params}`, {
            signal: controller.signal,
          });
          if (!response.ok) throw new Error("Catalog unavailable");
          const data: { works: Work[]; performances: Performance[] } =
            await response.json();
          if (controller.signal.aborted) return;
          works.push(...data.works);
          data.performances.forEach((performance) =>
            performances.set(performance.id, performance),
          );
        }
        setSelection({
          key: selectionKey,
          works,
          performances: [...performances.values()].sort((a, b) =>
            a.date.localeCompare(b.date),
          ),
          error: false,
        });
      } catch {
        if (!controller.signal.aborted)
          setSelection({
            key: selectionKey,
            works: [],
            performances: [],
            error: true,
          });
      }
    })();
    return () => controller.abort();
  }, [selectionKey, hasSelection]);
  const current = hasSelection && selection.key === selectionKey;
  const watchedWorks = current ? selection.works : [];
  const nextAlerts = current ? selection.performances : [];
  const catalogError = current && selection.error;
  const loading = authLoading || libraryLoading || (hasSelection && !current);

  return (
    <>
      <section>
        <div>
          <div className="flex items-center gap-2 text-sm font-black text-emerald-700">
            <Bell aria-hidden="true" className="size-4" />
            관심곡
          </div>
          <h1 className="mt-1 text-3xl font-black tracking-normal text-stone-950">
            내가 기다리는 작품
          </h1>

          {error ? (
            <p
              className="mt-5 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-800"
              role="alert"
            >
              {error}
            </p>
          ) : null}

          {loading ? (
            <div className="mt-6 flex min-h-48 items-center justify-center border-y border-stone-200 text-stone-500">
              <LoaderCircle
                aria-hidden="true"
                className="mr-2 size-5 animate-spin"
              />
              <span className="text-sm font-bold">불러오는 중</span>
            </div>
          ) : !user ? (
            <div className="mt-6 flex min-h-56 flex-col items-center justify-center border-y border-stone-200 px-4 text-center">
              <LogIn aria-hidden="true" className="size-7 text-stone-400" />
              <p className="mt-3 text-base font-black text-stone-950">
                로그인이 필요합니다
              </p>
              <button
                className="mt-4 inline-flex h-10 items-center gap-2 rounded-md bg-stone-950 px-4 text-sm font-black text-white transition hover:bg-emerald-800"
                onClick={() => signIn()}
                type="button"
              >
                <LogIn aria-hidden="true" className="size-4" />
                로그인
              </button>
            </div>
          ) : catalogError ? (
            <div role="alert" className="mt-6 py-8 text-sm text-stone-600">
              관심곡 정보를 불러오지 못했습니다.
              <button
                type="button"
                onClick={() => setRetry((value) => value + 1)}
                className="ml-3 font-bold text-emerald-800"
              >
                다시 시도
              </button>
            </div>
          ) : watchedWorks.length > 0 ? (
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {watchedWorks.map((work) => (
                <WorkCard
                  action={
                    <button
                      aria-label={`${workDisplay(work.title, work.titleKo, work.catalogue).heading} 관심곡 해제`}
                      className="grid size-9 place-items-center rounded-md text-stone-500 transition hover:bg-rose-50 hover:text-rose-700 disabled:opacity-45"
                      disabled={isPending(work.slug)}
                      onClick={() => void toggleWork(work.slug)}
                      title="관심곡 해제"
                      type="button"
                    >
                      {isPending(work.slug) ? (
                        <LoaderCircle
                          aria-hidden="true"
                          className="size-4 animate-spin"
                        />
                      ) : (
                        <BellOff aria-hidden="true" className="size-4" />
                      )}
                    </button>
                  }
                  key={work.slug}
                  work={work}
                />
              ))}
            </div>
          ) : (
            <div className="mt-6 flex min-h-56 flex-col items-center justify-center border-y border-stone-200 px-4 text-center">
              <Search aria-hidden="true" className="size-7 text-stone-400" />
              <p className="mt-3 text-base font-black text-stone-950">
                아직 담은 작품이 없습니다
              </p>
              <Link
                className="mt-4 inline-flex h-10 items-center gap-2 rounded-md bg-stone-950 px-4 text-sm font-black text-white transition hover:bg-emerald-800"
                href="/"
              >
                <Search aria-hidden="true" className="size-4" />
                공연 찾기
              </Link>
            </div>
          )}
        </div>

      </section>

      {user && !loading && watchedWorks.length > 0 ? (
        <section className="mt-8">
          <h2 className="text-2xl font-black tracking-normal text-stone-950">
            다음 알림 후보
          </h2>
          {nextAlerts.length > 0 ? (
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              {nextAlerts.map((performance, index) => (
                <PerformanceCard
                  compact
                  eager={index === 0}
                  key={performance.id}
                  performance={performance}
                />
              ))}
            </div>
          ) : (
            <p className="mt-4 border-y border-stone-200 py-8 text-sm font-bold text-stone-500">
              예정된 공연이 없습니다.
            </p>
          )}
        </section>
      ) : null}
    </>
  );
}
