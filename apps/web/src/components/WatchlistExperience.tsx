"use client";

import type { Performance, Work } from "@classic-hubble/shared";
import {
  Bell,
  BellOff,
  BellRing,
  LoaderCircle,
  LogIn,
  Mail,
  Search,
  Smartphone,
} from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { useAuth } from "./AuthProvider";
import { PerformanceCard } from "./PerformanceCard";
import { useUserLibrary } from "./UserLibraryProvider";
import { WorkCard } from "./WorkCard";

type WatchlistExperienceProps = {
  performances: Performance[];
  works: Work[];
};

export function WatchlistExperience({
  performances,
  works,
}: WatchlistExperienceProps) {
  const { loading: authLoading, openAuth, user } = useAuth();
  const {
    error,
    isPending,
    loading: libraryLoading,
    preferences,
    setPreference,
    toggleWork,
    watchedSlugs,
  } = useUserLibrary();

  const watchedWorks = useMemo(() => {
    const watched = new Set(watchedSlugs);
    return works.filter((work) => watched.has(work.slug));
  }, [watchedSlugs, works]);

  const nextAlerts = useMemo(() => {
    const watched = new Set(watchedSlugs);
    return performances.filter((performance) =>
      performance.program.some((item) => watched.has(item.workSlug)),
    );
  }, [performances, watchedSlugs]);

  const loading = authLoading || libraryLoading;

  return (
    <>
      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
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
              <LoaderCircle aria-hidden="true" className="mr-2 size-5 animate-spin" />
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
                onClick={() => openAuth("signin")}
                type="button"
              >
                <LogIn aria-hidden="true" className="size-4" />
                로그인
              </button>
            </div>
          ) : watchedWorks.length > 0 ? (
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {watchedWorks.map((work) => (
                <WorkCard
                  action={
                    <button
                      aria-label={`${work.titleKo} 관심곡 해제`}
                      className="grid size-9 place-items-center rounded-md text-stone-500 transition hover:bg-rose-50 hover:text-rose-700 disabled:opacity-45"
                      disabled={isPending(work.slug)}
                      onClick={() => void toggleWork(work.slug)}
                      title="관심곡 해제"
                      type="button"
                    >
                      {isPending(work.slug) ? (
                        <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
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

        {user && !loading ? (
          <aside>
            <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2">
                <BellRing aria-hidden="true" className="size-5 text-rose-700" />
                <h2 className="text-base font-black text-stone-950">알림 채널</h2>
              </div>
              <div className="mt-4 grid gap-3">
                <label className="flex items-center justify-between rounded-lg border border-stone-200 p-3">
                  <span className="inline-flex items-center gap-2 text-sm font-bold text-stone-700">
                    <Mail aria-hidden="true" className="size-4 text-sky-700" />
                    이메일
                  </span>
                  <input
                    checked={preferences.email}
                    className="size-4 accent-emerald-700"
                    onChange={(event) =>
                      void setPreference("email", event.target.checked)
                    }
                    type="checkbox"
                  />
                </label>
                <label className="flex items-center justify-between rounded-lg border border-stone-200 p-3 opacity-60">
                  <span className="inline-flex items-center gap-2 text-sm font-bold text-stone-700">
                    <Smartphone
                      aria-hidden="true"
                      className="size-4 text-emerald-700"
                    />
                    웹 푸시
                    <span className="text-xs text-stone-500">준비 중</span>
                  </span>
                  <input
                    checked={false}
                    className="size-4 accent-emerald-700"
                    disabled
                    readOnly
                    type="checkbox"
                  />
                </label>
              </div>
            </div>
          </aside>
        ) : null}
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
