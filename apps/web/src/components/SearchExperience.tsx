"use client";

import { useState, useSyncExternalStore } from "react";
import type { WorkSuggestion } from "@/lib/work-suggestions";
import { SearchBox } from "./SearchBox";
import { SearchResults } from "./SearchResults";

export type SearchState = { query: string; work: string; mode: "works" | "performances"; city: string };
type Props = { initialQuery?: string; initialWork?: string; initialMode?: SearchState["mode"]; initialCity?: string };

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
  return params.size ? `?${params}` : "";
}

export function SearchExperience({ initialQuery = "", initialWork = "", initialMode = "works", initialCity = "전체" }: Props) {
  // A cached Next.js page may have old initial props when restored from a detail page.
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, () => searchString({ query: initialQuery, work: initialWork, mode: initialMode, city: initialCity }));
  const params = new URLSearchParams(snapshot);
  const candidate = params.get("work") ?? "";
  const search: SearchState = {
    query: (params.get("q") ?? params.get("composer") ?? "").slice(0, 200).trim(),
    work: /^[a-z0-9-]{1,160}$/.test(candidate) ? candidate : "",
    mode: params.get("mode") === "performances" ? "performances" : "works",
    city: (params.get("city") ?? "").slice(0, 80) || "전체",
  };
  const [page, setPage] = useState({ snapshot, offset: 0 });
  const offset = page.snapshot === snapshot ? page.offset : 0;
  const submitted = !!(search.query || search.work);
  function commit(next: SearchState) {
    const nextSnapshot = searchString(next);
    const url = `/${nextSnapshot}`;
    setPage({ snapshot: nextSnapshot, offset: 0 });
    if (location.pathname + location.search !== url) window.history.pushState({}, "", url);
    window.dispatchEvent(new Event(changeEvent));
  }
  const clear = () => commit({ query: "", work: "", mode: "works", city: "전체" });
  const select = (work: WorkSuggestion) => commit({ query: work.title, work: work.slug, mode: "works", city: "전체" });

  return (
    <div className={submitted ? "mx-auto w-full max-w-4xl px-4 pb-16 pt-6 sm:px-8 sm:pt-10" : "mx-auto flex min-h-[calc(100svh-12rem)] w-full max-w-3xl flex-col justify-center px-4 pb-24 sm:px-8"}>
      {!submitted ? <h1 className="mb-8 text-center text-3xl font-medium text-neutral-900 sm:text-4xl">클래식허블</h1> : null}
      <div className={submitted ? "mx-auto max-w-3xl" : ""}>
        <SearchBox initialValue={search.query} onSubmit={query => commit({ ...search, query, work: "" })} onSelect={select} onClear={clear} />
      </div>
      {submitted ? <SearchResults search={search} offset={offset} onMore={() => setPage({ snapshot, offset: offset + 24 })}
        onMode={mode => commit({ ...search, mode, work: "" })} onCity={city => commit({ ...search, city })} /> : null}
    </div>
  );
}
