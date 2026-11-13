"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { composerDiscoveryHref, type ComposerDirectoryEntry } from "@/lib/composer-directory";
import type { WorkSuggestion } from "@/lib/work-suggestions";
import { concertPeriod, type ConcertPeriod } from "@/lib/catalog-search";
import { SearchBox } from "./SearchBox";
import { SearchResults } from "./SearchResults";
import { SingleLineText } from "./SingleLineText";
import { useYouTubeLookup, YouTubeResults } from "./YouTubeSearch";

export type SearchState = { query: string; work: string; mode: "works" | "performances"; city: string; period: ConcertPeriod };
type Props = { initialQuery?: string; initialWork?: string; initialMode?: SearchState["mode"]; initialCity?: string; initialPeriod?: ConcertPeriod };

const changeEvent = "catalog-search-change";
function subscribe(listener: () => void) {
  window.addEventListener("popstate", listener);
  window.addEventListener(changeEvent, listener);
  return () => { window.removeEventListener("popstate", listener); window.removeEventListener(changeEvent, listener); };
}
const getSnapshot = () => window.location.search;
function searchString(search: SearchState) {
  const params = new URLSearchParams();
  if (search.query) params.set("q", search.query);
  if (search.work) params.set("work", search.work);
  if (search.mode === "performances") params.set("mode", search.mode);
  if (search.city !== "전체") params.set("city", search.city);
  if (search.period !== "all") params.set("period", search.period);
  return params.size ? `?${params}` : "";
}

export function SearchExperience({ initialQuery = "", initialWork = "", initialMode = "works", initialCity = "전체", initialPeriod = "all" }: Props) {
  const router = useRouter();
  const openComposer = useCallback((person: ComposerDirectoryEntry) => router.push(composerDiscoveryHref(person)), [router]);
  // A cached Next.js page may have old initial props when restored from a detail page.
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, () => searchString({ query: initialQuery, work: initialWork, mode: initialMode, city: initialCity, period: initialPeriod }));
  const params = new URLSearchParams(snapshot);
  const candidate = params.get("work") ?? "";
  const search: SearchState = {
    query: (params.get("q") ?? params.get("composer") ?? "").slice(0, 200).trim(),
    work: /^[a-z0-9-]{1,160}$/.test(candidate) ? candidate : "",
    mode: params.get("mode") === "performances" ? "performances" : "works",
    city: (params.get("city") ?? "").slice(0, 80) || "전체",
    period: concertPeriod(params.get("period")),
  };
  const [page, setPage] = useState({ snapshot, offset: 0 });
  const offset = page.snapshot === snapshot ? page.offset : 0;
  const lookup = useYouTubeLookup();
  const { reset } = lookup;
  const [navigation, setNavigation] = useState(0);
  useEffect(() => {
    const restore = () => { reset(); setNavigation(n => n + 1); };
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, [reset]);
  const showingVideo = !!(lookup.loading || lookup.error || lookup.video);
  const submitted = showingVideo || !!(search.query || search.work);
  const [showEntrance, setShowEntrance] = useState(!submitted);
  function commit(next: SearchState) {
    reset();
    setShowEntrance(false);
    const nextSnapshot = searchString(next);
    const url = `/${nextSnapshot}`;
    setPage({ snapshot: nextSnapshot, offset: 0 });
    if (location.pathname + location.search !== url) window.history.pushState({}, "", url);
    window.dispatchEvent(new Event(changeEvent));
  }
  const clear = () => commit({ query: "", work: "", mode: "works", city: "전체", period: "all" });
  const select = (work: WorkSuggestion) => commit({ query: work.title, work: work.slug, mode: "works", city: "전체", period: "all" });

  return (
    <div className={submitted ? "mx-auto w-full max-w-4xl px-4 pb-16 pt-6 sm:px-8 sm:pt-10" : "mx-auto flex min-h-[calc(100svh-12rem)] w-full max-w-3xl flex-col justify-center px-4 pb-24 sm:px-8"}>
      {!submitted ? (
        <h1
          className={`mb-8 text-center text-2xl leading-snug font-medium text-neutral-900 sm:text-3xl${showEntrance ? " search-welcome-enter" : ""}`}
          onAnimationEnd={() => setShowEntrance(false)}
        >
          <SingleLineText>어떤 곡을 공연장에서 듣고 싶으세요?</SingleLineText>
        </h1>
      ) : null}
      <div className={submitted ? "mx-auto max-w-3xl" : ""}>
        <SearchBox key={navigation} initialValue={search.query} onSubmit={query => commit({ ...search, query, work: "" })} onSelect={select} onComposer={openComposer} onClear={clear}
          onVideo={(id, retry) => {
            if (!id) { reset(); return; }
            setShowEntrance(false);
            void lookup.identify(id, retry && !!lookup.error);
          }} />
      </div>
      {showingVideo ? <>
        {lookup.error && <p role="alert" className="mt-4 text-sm text-red-700">{lookup.error}</p>}
        <YouTubeResults lookup={lookup} inline />
      </> : submitted ? <SearchResults search={search} offset={offset} onMore={() => setPage({ snapshot, offset: offset + 24 })}
        onMode={mode => commit({ ...search, mode, work: "" })} onCity={city => commit({ ...search, city })}
        onPeriod={period => commit({ ...search, period })} /> : null}
    </div>
  );
}
