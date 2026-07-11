"use client";

import { BellPlus, BellRing, LoaderCircle } from "lucide-react";

import { useUserLibrary } from "./UserLibraryProvider";

type WatchlistButtonProps = {
  workSlug: string;
};

export function WatchlistButton({ workSlug }: WatchlistButtonProps) {
  const { isPending, isWatched, loading, toggleWork } = useUserLibrary();
  const watched = isWatched(workSlug);
  const pending = isPending(workSlug);
  const label = loading
    ? "관심곡 확인 중"
    : pending
      ? "관심곡 저장 중"
      : watched
        ? "알림 받는 중"
        : "이 곡 알림 받기";

  return (
    <button
      aria-pressed={watched}
      className={`inline-flex h-11 w-full items-center justify-center gap-2 rounded-md px-4 text-sm font-black transition disabled:cursor-wait disabled:opacity-60 ${
        watched
          ? "border border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
          : "bg-stone-950 text-white hover:bg-emerald-800"
      }`}
      disabled={loading || pending}
      onClick={() => void toggleWork(workSlug)}
      type="button"
    >
      {loading || pending ? (
        <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
      ) : watched ? (
        <BellRing aria-hidden="true" className="size-4" />
      ) : (
        <BellPlus aria-hidden="true" className="size-4" />
      )}
      {label}
    </button>
  );
}
