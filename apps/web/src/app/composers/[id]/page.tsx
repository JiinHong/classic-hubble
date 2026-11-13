import { ArrowLeft, ArrowRight, ChevronLeft, ChevronRight, UserRound } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import { composerBiography } from "@/lib/composer-biography";
import { composerDiscoveryHref, PERIOD_LABELS } from "@/lib/composer-directory";
import { getComposerProfile, PROFILE_PAGE_SIZE } from "@/lib/composer-profile";

type Props = { params: Promise<{ id: string }>; searchParams: Promise<{ page?: string | string[] }> };

export default async function ComposerPage({ params, searchParams }: Props) {
  const { id: segment } = await params;
  let id: string;
  try {
    id = decodeURIComponent(segment);
  } catch {
    notFound();
  }
  const { page: requested } = await searchParams;
  const page = requested === undefined ? 1 : typeof requested === "string" && /^[1-9]\d{0,4}$/.test(requested) ? Number(requested) : 0;
  if (!page) notFound();
  const profile = await getComposerProfile(id, page);
  if (!profile || (page > 1 && !profile.works.length)) notFound();
  const { composer, works, count } = profile;
  const bio = composerBiography(composer, count);
  const base = composerDiscoveryHref(composer);
  const pages = Math.ceil(count / PROFILE_PAGE_SIZE);
  return <main className="mx-auto w-full max-w-3xl px-5 pt-5 pb-16 sm:px-8 sm:pt-8">
    <Link href="/composers" className="inline-flex min-h-10 items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900"><ArrowLeft className="size-4" aria-hidden="true" />작곡가 목록</Link>
    <header className="mt-6 grid grid-cols-[5rem_minmax(0,1fr)] items-center gap-x-5 gap-y-4 sm:grid-cols-[8rem_minmax(0,1fr)] sm:gap-x-7">
      <div className="grid aspect-square place-items-center overflow-hidden rounded-lg bg-neutral-100 text-neutral-400 sm:row-span-2">
        {composer.portraitSrc ? <Image alt={composer.nameKo + " 초상"} src={composer.portraitSrc} width={128} height={128} loading="eager" className="size-full object-cover" /> : <UserRound aria-hidden="true" className="size-10" />}
      </div>
      <div>
        <p className="mb-1 text-xs font-medium text-emerald-800">{composer.period === "other" ? "작곡가" : PERIOD_LABELS[composer.period] + " · 작곡가"}</p>
        <h1 className="break-keep text-xl leading-snug font-semibold sm:text-3xl">{composer.nameKo}</h1>
        {composer.name !== composer.nameKo && <p className="mt-1 break-words text-sm text-neutral-500">{composer.name}</p>}
      </div>
      <div className="col-span-2 text-sm leading-relaxed text-neutral-700 sm:col-span-1">
        <p>{bio.text}</p>
        {bio.href && <a href={bio.href} className="mt-1 inline-block text-xs text-neutral-500 underline decoration-neutral-300 underline-offset-2">{bio.source}</a>}
      </div>
    </header>
    <section className="mt-9" aria-labelledby="composer-works">
      <div className="flex items-baseline justify-between gap-3 border-b border-neutral-300 pb-3">
        <h2 id="composer-works" className="text-lg font-semibold">작품 <span className="ml-1 text-sm font-normal text-neutral-500">{count.toLocaleString("ko")}</span></h2>
        <Link href={"/?" + new URLSearchParams({ q: composer.nameKo, mode: "performances" })} className="inline-flex items-center gap-1 text-sm text-emerald-800 hover:underline">공연 찾기<ArrowRight className="size-4" aria-hidden="true" /></Link>
      </div>
      {works.length ? <ul className="divide-y divide-neutral-100">{works.map(w => <li key={w.slug}>
        <Link prefetch={false} href={"/works/" + encodeURIComponent(w.slug)} className="group flex min-h-16 items-center justify-between gap-4 py-3">
          <div className="min-w-0"><p className="break-words font-medium group-hover:text-emerald-800">{w.title_ko || w.title}</p>
            {(w.catalogue || (w.title_ko && w.title !== w.title_ko)) && <p className="mt-0.5 break-words text-sm text-neutral-500">{[w.title_ko && w.title !== w.title_ko ? w.title : "", w.catalogue && !w.title.includes(w.catalogue) ? w.catalogue : ""].filter(Boolean).join(" · ") || w.catalogue}</p>}</div>
          <ChevronRight className="size-4 shrink-0 text-neutral-400" aria-hidden="true" />
        </Link></li>)}</ul> : <p className="mt-5 text-sm text-neutral-500">아직 연결된 작품이 없습니다.</p>}
      {pages > 1 && <nav aria-label="작품 페이지" className="mt-4 flex items-center justify-center gap-5 text-sm">
        {page > 1 && <Link href={page === 2 ? base : base + "?page=" + (page - 1)} aria-label="이전 작품 페이지" className="icon-button"><ChevronLeft className="size-4" /></Link>}
        <span className="tabular-nums text-neutral-500">{page} / {pages}</span>
        {page < pages && <Link href={base + "?page=" + (page + 1)} aria-label="다음 작품 페이지" className="icon-button"><ChevronRight className="size-4" /></Link>}
      </nav>}
    </section>
  </main>;
}
