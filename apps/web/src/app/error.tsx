"use client";
import { RefreshCw } from "lucide-react";

export default function ErrorPage({
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div role="alert" className="space-y-3">
        <h1 className="text-xl font-bold">정보를 불러오지 못했습니다.</h1>
        <p className="text-stone-600">잠시 후 다시 시도해 주세요.</p>
        <button
          onClick={reset}
          type="button"
          className="inline-flex h-10 items-center gap-2 font-semibold text-emerald-700"
        >
          <RefreshCw aria-hidden="true" className="size-4" />
          다시 시도
        </button>
      </div>
    </main>
  );
}
