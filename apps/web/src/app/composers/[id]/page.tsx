import { ArrowLeft, ArrowRight, Check, ChevronDown, ChevronLeft, ChevronRight, SlidersHorizontal, UserRound } from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import { composerBiography } from "@/lib/composer-biography";
import { composerDiscoveryHref, PERIOD_LABELS } from "@/lib/composer-directory";
import { getComposerProfile, PROFILE_PAGE_SIZE } from "@/lib/composer-profile";
import { formLabels, type Form } from "@/lib/work-forms";
import type { WorkNode } from "@/lib/composer-repertoire";

type Props = { params: Promise<{ id: string }>; searchParams: Promise<{ page?: string | string[]; genre?: string | string[] }> };

function browseHref(base: string, genre?: Form, page = 1) {
  const q = new URLSearchParams();
  if (genre) q.set("genre", genre);
  if (page > 1) q.set("page", String(page));
  return base + (q.size ? "?" + q : "");
}

function WorkItem({ work: w }: { work: WorkNode }) {
  const normalizeCatalogue = (s: string) => s.toLowerCase().replace(/[\s.,]/g, "");
  const subtitle = [w.title_ko && w.title !== w.title_ko ? w.title : "",
    w.catalogue && !normalizeCatalogue(w.title).includes(normalizeCatalogue(w.catalogue)) ? w.catalogue : ""].filter(Boolean).join(" · ");
  return <li className="py-1">
    <Link prefetch={false} href={"/works/" + encodeURIComponent(w.slug)} className="group flex min-h-14 items-center justify-between gap-4 py-2">
      <div className="min-w-0"><p className="break-words font-medium group-hover:text-emerald-800">{w.title_ko || w.title}</p>
        {subtitle && <p className="mt-0.5 break-words text-sm text-neutral-500">{subtitle}</p>}</div>
      <ChevronRight className="size-4 shrink-0 text-neutral-400" aria-hidden="true" />
    </Link>
    {w.alternate && <Link prefetch={false} href={"/works/" + encodeURIComponent(w.alternate.slug)} className="mb-2 inline-block text-xs text-neutral-600 underline">같은 악장의 다른 등록명: {w.alternate.title_ko || w.alternate.title}</Link>}
    {w.parts.length > 0 && <details className="mb-2">
      <summary className="inline-flex min-h-9 cursor-pointer list-none items-center gap-1 text-sm text-emerald-800 [&::-webkit-details-marker]:hidden [[open]>&>svg]:rotate-180">
        악장 · 구성곡 {w.parts.length}<ChevronDown aria-hidden="true" className="size-4" />
      </summary>
      <ul className="ml-1 divide-y divide-neutral-100 border-l-2 border-neutral-200 pl-4">{w.parts.map(part => <WorkItem key={part.slug} work={part} />)}</ul>
    </details>}
  </li>;
}

export default async function ComposerPage({ params, searchParams }: Props) {
  const { id: segment } = await params;
  let id: string;
  try {
    id = decodeURIComponent(segment);
  } catch {
    notFound();
  }
  const { page: requested, genre: rawGenre } = await searchParams;
  if (rawGenre !== undefined && (typeof rawGenre !== "string" || !formLabels.has(rawGenre as Form))) notFound();
  const genre = rawGenre as Form | undefined;
  const page = requested === undefined ? 1 : typeof requested === "string" && /^[1-9]\d{0,4}$/.test(requested) ? Number(requested) : 0;
  if (!page) notFound();
  const profile = await getComposerProfile(id, page, genre);
  if (!profile || ((page > 1 || genre) && !profile.works.length)) notFound();
  const { composer, works, count, selectedCount, facets } = profile;
  const bio = composerBiography(composer, count);
  const base = composerDiscoveryHref(composer);
  const pages = Math.ceil(selectedCount / PROFILE_PAGE_SIZE);
  const options = [{id: undefined, label: "전체", count}, ...facets];
  const visible = options.filter((f,i) => i < 8 || f.id === genre);
  const more = options.filter(f => !visible.includes(f));
  const chip = (option: typeof options[number]) => <Link key={option.id || "all"} scroll={false} prefetch={false}
    href={browseHref(base, option.id)} aria-current={option.id === genre ? "true" : undefined}
    className={"inline-flex min-h-9 items-center gap-1.5 rounded-full border px-3 py-1 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 " +
      (option.id === genre ? "border-emerald-900 bg-emerald-900 text-white" : "border-neutral-200 bg-white text-neutral-700 hover:border-neutral-400")}>
    {option.id === genre && <Check className="size-3.5" aria-hidden="true" />}
    {option.label}<span className={"text-xs tabular-nums " + (option.id === genre ? "text-emerald-100" : "text-neutral-500")}>{option.count}</span>
  </Link>;
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
        <h2 id="composer-works" className="text-lg font-semibold">작품 <span className="ml-1 text-sm font-normal text-neutral-500">{count.toLocaleString("ko")}{profile.componentCount > 0 && " · 구성곡 " + profile.componentCount.toLocaleString("ko")}</span></h2>
        <Link href={"/?" + new URLSearchParams({ q: composer.nameKo, mode: "performances" })} className="inline-flex items-center gap-1 text-sm text-emerald-800 hover:underline">공연 찾기<ArrowRight className="size-4" aria-hidden="true" /></Link>
      </div>
      {count > 0 && <nav aria-label="작품 종류" className="border-b border-neutral-200 py-4">
        <div className="flex flex-wrap gap-2">{visible.map(chip)}</div>
        {more.length > 0 && <details key={genre || "all"} className="mt-2">
          <summary className="inline-flex min-h-9 cursor-pointer list-none items-center gap-1.5 text-sm text-neutral-600 hover:text-neutral-900 [&::-webkit-details-marker]:hidden">
            <SlidersHorizontal aria-hidden="true" className="size-3.5" />다른 종류 {more.length}<ChevronDown aria-hidden="true" className="size-3.5" />
          </summary>
          <div className="mt-2 flex flex-wrap gap-2">{more.map(chip)}</div>
        </details>}
      </nav>}
      {works.length ? <ul aria-label={genre ? formLabels.get(genre) : "전체 작품"} className="divide-y divide-neutral-100">{works.map(w => <WorkItem key={w.slug} work={w} />)}</ul>
        : <p className="mt-5 text-sm text-neutral-500">아직 연결된 작품이 없습니다.</p>}
      {pages > 1 && <nav aria-label="작품 페이지" className="mt-4 flex items-center justify-center gap-5 text-sm">
        {page > 1 && <Link href={browseHref(base, genre, page - 1)} aria-label="이전 작품 페이지" className="icon-button"><ChevronLeft className="size-4" /></Link>}
        <span className="tabular-nums text-neutral-500">{page} / {pages}</span>
        {page < pages && <Link href={browseHref(base, genre, page + 1)} aria-label="다음 작품 페이지" className="icon-button"><ChevronRight className="size-4" /></Link>}
      </nav>}
    </section>
  </main>;
}
