import type { Metadata } from "next";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { YouTubeSearch } from "@/components/YouTubeSearch";
export const metadata: Metadata = {
  title: "유튜브로 작품 찾기 | Classic Hubble",
};

export default function YouTubePage() {
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
      <YouTubeSearch />
    </main>
  );
}
