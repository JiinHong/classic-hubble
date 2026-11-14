"use client";

import { Bell, Check, LoaderCircle } from "lucide-react";

import { useUserLibrary } from "./UserLibraryProvider";

type WatchlistButtonProps = {
  workSlug: string;
};

export function WatchlistButton({ workSlug }: WatchlistButtonProps) {
  const { isPending, isWatched, loading, toggleWork } = useUserLibrary();
  const watched = isWatched(workSlug);
  const pending = isPending(workSlug);
  const label = watched ? "알림 받는 중" : "공연 알림 받기";

  return (
    <button
      aria-pressed={watched}
      aria-busy={loading || pending}
      className={`inline-flex h-11 min-w-32 items-center justify-center gap-2 rounded-full border px-4 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 disabled:cursor-wait ${
        watched
          ? "border-emerald-200 bg-emerald-50 text-emerald-800 hover:border-emerald-400"
          : "border-neutral-300 bg-white text-neutral-900 hover:border-neutral-600 hover:bg-neutral-50"
      }`}
      disabled={loading || pending}
      onClick={() => void toggleWork(workSlug)}
      type="button"
    >
      {loading || pending ? (
        <LoaderCircle aria-hidden="true" className="size-4 animate-spin motion-reduce:animate-none" />
      ) : watched ? (
        <Check aria-hidden="true" className="size-4" />
      ) : (
        <Bell aria-hidden="true" className="size-4" />
      )}
      {label}
    </button>
  );
}
