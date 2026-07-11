import { Check, ScanText, X } from "lucide-react";
import Image from "next/image";

import { getCatalogSnapshot } from "@/lib/catalog";
import { confidenceLabel } from "@/lib/format";

export default async function ReviewPage() {
  const catalog = await getCatalogSnapshot();
  const pendingItems = catalog.reviewQueue.filter((item) => item.state === "needs_review");

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-center gap-2 text-sm font-black text-amber-700">
        <ScanText aria-hidden="true" className="size-4" />
        운영 검수
      </div>
      <h1 className="mt-1 text-3xl font-black tracking-normal text-stone-950">
        이미지 프로그램 매칭 큐
      </h1>

      <section className="mt-6 grid gap-4">
        {pendingItems.map((item) => {
          const performance = catalog.performances.find(
            (catalogPerformance) => catalogPerformance.id === item.performanceId,
          );
          const suggestedWork = item.suggestedWorkSlug
            ? catalog.works.find((work) => work.slug === item.suggestedWorkSlug)
            : null;

          return (
            <article
              key={item.id}
              className="grid overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm lg:grid-cols-[220px_minmax(0,1fr)_220px]"
            >
              <div className="relative min-h-64 bg-stone-100">
                <Image
                  src={item.imageUrl}
                  alt={`${performance?.title ?? item.id} 포스터`}
                  className="absolute inset-0 h-full w-full object-cover"
                  fill
                  sizes="(min-width: 1024px) 220px, 100vw"
                  unoptimized
                />
              </div>

              <div className="min-w-0 p-5">
                <p className="text-sm font-black text-stone-500">{performance?.venue}</p>
                <h2 className="mt-1 text-xl font-black tracking-normal text-stone-950">
                  {performance?.title}
                </h2>

                <div className="mt-5 rounded-lg border border-stone-200 bg-stone-50 p-4">
                  <p className="text-xs font-black text-stone-500">OCR 텍스트</p>
                  <p className="mt-2 text-sm font-semibold leading-6 text-stone-700">
                    {item.extractedText}
                  </p>
                </div>

                <div className="mt-4">
                  <p className="text-xs font-black text-stone-500">추천 매칭</p>
                  <p className="mt-1 text-base font-black text-stone-950">
                    {suggestedWork
                      ? `${suggestedWork.composer.nameKo} · ${suggestedWork.titleKo}`
                      : "매칭 없음"}
                  </p>
                  <p className="mt-1 text-sm font-semibold text-amber-700">
                    신뢰도 {confidenceLabel(item.confidence)}
                  </p>
                </div>
              </div>

              <div className="flex flex-col justify-end gap-2 border-t border-stone-200 p-5 lg:border-l lg:border-t-0">
                <button
                  type="button"
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-stone-950 px-4 text-sm font-black text-white transition hover:bg-emerald-800"
                >
                  <Check aria-hidden="true" className="size-4" />
                  승인
                </button>
                <button
                  type="button"
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-stone-200 px-4 text-sm font-black text-stone-700 transition hover:bg-stone-100"
                >
                  <X aria-hidden="true" className="size-4" />
                  보류
                </button>
              </div>
            </article>
          );
        })}
      </section>
    </main>
  );
}
