import type { Metadata } from "next";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { YouTubeSearch } from "@/components/YouTubeSearch";
import { getCatalogSnapshot } from "@/lib/catalog";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "유튜브로 작품 찾기 | Classic Hubble",
};

export default async function YouTubePage() {
  const catalog = await getCatalogSnapshot();
  return (
    <main className="mx-auto min-h-[65vh] max-w-4xl px-4 py-8 sm:px-6">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm font-semibold text-stone-600 hover:text-stone-950"
      >
        <ArrowLeft aria-hidden="true" className="size-4" />
        탐색으로
      </Link>
      <h1 className="mb-7 mt-6 text-2xl font-black text-stone-950">
        유튜브로 작품 찾기
      </h1>
      {catalog.source === "unavailable" ? (
        <p role="alert" className="text-sm text-stone-600">
          작품 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.
        </p>
      ) : (
        <YouTubeSearch works={catalog.works} />
      )}
    </main>
  );
}
