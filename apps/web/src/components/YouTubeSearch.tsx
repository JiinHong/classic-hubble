"use client";

import { ArrowUpRight, Link2, LoaderCircle, Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { parseYouTubeUrl, type YouTubeVideo } from "@/lib/youtube";
import {
  type YouTubeWorkEntry,
  type YouTubeMatchReason,
} from "@/lib/youtube-matching";
import { WorkCard } from "./WorkCard";

const errors: Record<string, string> = {
  catalog_unavailable:
    "작품 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.",
  invalid_url: "올바른 유튜브 영상 링크를 입력해 주세요.",
  invalid_request: "영상 링크를 확인해 주세요.",
  video_unavailable:
    "영상을 불러올 수 없습니다. 비공개·삭제된 영상이거나 접근할 수 없는 영상입니다.",
  quota_exceeded:
    "오늘의 유튜브 조회 한도에 도달했습니다. 잠시 후 다시 이용해 주세요.",
  rate_limited: "요청이 많습니다. 1분 후 다시 시도해 주세요.",
  not_configured: "유튜브 검색 연결을 준비 중입니다.",
  timeout: "유튜브 응답이 지연되고 있습니다. 다시 시도해 주세요.",
  upstream_error:
    "영상 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.",
};
const reasons: Record<YouTubeMatchReason, string> = {
  composer_catalogue: "작곡가·작품번호 일치",
  composer_title: "작곡가·작품명 일치",
  distinctive_title: "작품명·별칭 일치",
};

export function YouTubeSearch() {
  const [input, setInput] = useState("");
  const [video, setVideo] = useState<YouTubeVideo | null>(null);
  const [result, setResult] = useState<{ entries: YouTubeWorkEntry[] } | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  function changeInput(value: string) {
    pending.current?.abort();
    pending.current = null;
    setInput(value);
    setVideo(null);
    setResult(null);
    setError(null);
    setLoading(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const id = parseYouTubeUrl(input);
    if (!id) {
      setError(errors.invalid_url);
      return;
    }
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setVideo(null);
    setResult(null);
    setError(null);
    setLoading(true);
    try {
      const response = await fetch("/api/youtube", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: `https://www.youtube.com/watch?v=${id}` }),
        signal: controller.signal,
      });
      const body = await response.json();
      if (controller.signal.aborted || pending.current !== controller) return;
      if (!response.ok || !body.video || !body.result) {
        setError(errors[body.error] ?? errors.upstream_error);
        return;
      }
      setVideo(body.video);
      setResult(body.result);
    } catch {
      if (!controller.signal.aborted && pending.current === controller)
        setError(errors.upstream_error);
    } finally {
      if (pending.current === controller) setLoading(false);
    }
  }

  return (
    <div className="min-w-0">
      <form onSubmit={submit} className="border-b border-stone-200 pb-6">
        <label
          htmlFor="youtube-url"
          className="mb-2 block text-sm font-bold text-stone-700"
        >
          유튜브 영상 링크
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative min-w-0 flex-1">
            <Link2
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-4 size-5 text-stone-400"
            />
            <input
              id="youtube-url"
              type="text"
              inputMode="url"
              autoComplete="off"
              maxLength={2048}
              spellCheck={false}
              value={input}
              onChange={(event) => changeInput(event.target.value)}
              placeholder="https://www.youtube.com/watch?v=…"
              aria-invalid={Boolean(error)}
              aria-describedby={error ? "youtube-error" : undefined}
              className="h-13 w-full min-w-0 rounded-md border border-stone-300 bg-white pl-10 pr-3 text-base text-stone-950 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex h-13 shrink-0 items-center justify-center gap-2 rounded-md bg-emerald-800 px-6 text-sm font-bold text-white hover:bg-emerald-900 disabled:opacity-50"
          >
            {loading ? (
              <LoaderCircle
                aria-hidden="true"
                className="size-4 animate-spin"
              />
            ) : (
              <Search aria-hidden="true" className="size-4" />
            )}
            {loading ? "찾는 중" : "작품 찾기"}
          </button>
        </div>
        {error && (
          <p
            id="youtube-error"
            role="alert"
            className="mt-3 text-sm text-red-700"
          >
            {error}
          </p>
        )}
      </form>

      <div aria-live="polite" aria-busy={loading}>
        {loading && (
          <p role="status" className="py-8 text-sm text-stone-500">
            영상 정보를 확인하고 있습니다.
          </p>
        )}
        {video && (
          <>
            <div className="flex min-w-0 flex-col gap-4 border-b border-stone-200 py-6 sm:flex-row">
              <a
                href={`https://www.youtube.com/watch?v=${video.id}`}
                target="_blank"
                rel="noreferrer"
                aria-label="YouTube에서 영상 열기"
                className="block aspect-video w-full shrink-0 overflow-hidden rounded-md bg-stone-100 sm:w-48"
              >
                {/* The thumbnail uses a validated video ID, never a provider-supplied URL. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`https://i.ytimg.com/vi/${video.id}/mqdefault.jpg`}
                  alt=""
                  width={320}
                  height={180}
                  referrerPolicy="no-referrer"
                  className="h-full w-full object-cover"
                />
              </a>
              <div className="min-w-0 self-center">
                <p className="text-xs font-bold text-red-700">YouTube</p>
                <h2 className="mt-1 break-words text-lg font-bold leading-7 text-stone-950">
                  {video.title}
                </h2>
                <p className="mt-1 break-words text-sm text-stone-500">
                  {video.channelTitle}
                </p>
                <a
                  href={`https://www.youtube.com/watch?v=${video.id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-stone-700 hover:underline"
                >
                  YouTube에서 보기
                  <ArrowUpRight aria-hidden="true" className="size-4" />
                </a>
              </div>
            </div>

            {result?.entries.length ? (
              <section className="py-6" aria-labelledby="youtube-results">
                <h2
                  id="youtube-results"
                  className="text-xl font-bold text-stone-950"
                >
                  관련 작품 후보
                </h2>
                <p className="mt-2 text-sm leading-6 text-stone-500">
                  영상 제목·설명에 근거한 검색 후보입니다. 실제 연주 내용과 다를
                  수 있습니다.
                </p>
                <div className="mt-6 space-y-8">
                  {result.entries.map((entry, index) => (
                    <section key={index} className="min-w-0">
                      <blockquote className="mb-3 break-words border-l-2 border-stone-300 pl-3 text-sm leading-6 text-stone-600">
                        {entry.text}
                      </blockquote>
                      {entry.ambiguous && (
                        <p className="mb-3 text-sm font-semibold text-amber-800">
                          작품 확인이 필요합니다 · 상위{" "}
                          {entry.candidates.length}개 후보
                        </p>
                      )}
                      <div className="grid gap-4 sm:grid-cols-2">
                        {entry.candidates.map(({ work, reason }) => (
                          <div key={work.slug} className="min-w-0">
                            <p className="mb-2 text-xs font-semibold text-stone-500">
                              {reasons[reason]}
                            </p>
                            <WorkCard
                              work={work}
                              action={
                                <Link
                                  href={`/works/${work.slug}`}
                                  className="inline-flex shrink-0 items-center gap-1 font-semibold text-emerald-800 hover:underline"
                                >
                                  공연 보기
                                  <ArrowUpRight
                                    aria-hidden="true"
                                    className="size-4"
                                  />
                                </Link>
                              }
                            />
                          </div>
                        ))}
                      </div>
                    </section>
                  ))}
                </div>
              </section>
            ) : (
              <section className="py-10">
                <h2 className="text-lg font-bold text-stone-950">
                  작품을 찾지 못했습니다.
                </h2>
                <p className="mt-2 text-sm leading-6 text-stone-500">
                  영상의 작품 정보가 부족하거나 아직 작품 DB와 연결하지
                  못했습니다.
                </p>
                <Link
                  href="/"
                  className="mt-4 inline-flex items-center gap-1 text-sm font-bold text-emerald-800"
                >
                  곡명으로 검색
                  <ArrowUpRight aria-hidden="true" className="size-4" />
                </Link>
              </section>
            )}
          </>
        )}
      </div>
      <p className="mt-6 text-xs leading-6 text-stone-500">
        YouTube API Services 사용 ·{" "}
        <a
          href="https://www.youtube.com/t/terms"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          YouTube 이용약관
        </a>{" "}
        ·{" "}
        <Link href="/youtube/privacy" className="underline">
          데이터 처리 안내
        </Link>
      </p>
    </div>
  );
}
