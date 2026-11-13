"use client";

import { ArrowRight, ArrowUpLeft, UserRound, X, Youtube } from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";
import starterData from "@/data/starter-suggestions.json";
import { matchComposers } from "@/lib/composer-search";
import { PERIOD_LABELS, type ComposerDirectoryEntry } from "@/lib/composer-directory";
import type { WorkSuggestion } from "@/lib/work-suggestions";
import { parseYouTubeUrl } from "@/lib/youtube";
import { SingleLineText } from "./SingleLineText";

type Props = {
  initialValue: string;
  onSubmit: (query: string) => void;
  onSelect: (work: WorkSuggestion) => void;
  onComposer?: (person: ComposerDirectoryEntry) => void;
  onClear: () => void;
  onVideo: (id: string | null, retry?: boolean) => void;
};

const looksLikeLink = (text: string) => /^(?:[a-z][a-z\d+.-]*:\/\/|(?:www\.|m\.|music\.)?(?:youtube(?:-nocookie)?\.com|youtu\.be)(?:[/?#:]|$))/i.test(text.trim());
const starters: Record<string, WorkSuggestion[]> = starterData;
const limitDraft = (raw: string) => looksLikeLink(raw) ? raw : raw.slice(0, 200);

type Option = WorkSuggestion & { person?: ComposerDirectoryEntry };

export function SearchBox({ initialValue, onSubmit, onSelect, onComposer, onClear, onVideo }: Props) {
  const [linkHint, setLinkHint] = useState(false);
  const [invalidLink, setInvalidLink] = useState(false);
  const searchPlaceholder = linkHint ? "마음에 드는 클래식 음악의 유튜브 링크를 넣어보세요" : "클래식 곡명이나 작곡가를 입력하세요";
  const [value, setValue] = useState(initialValue);
  const [lastInitialValue, setLastInitialValue] = useState(initialValue);
  const [open, setOpen] = useState(false);
  const [composing, setComposing] = useState(false);
  const composingRef = useRef(false);
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [result, setResult] = useState({ query: "", items: [] as WorkSuggestion[], error: false });
  const root = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const lastDomInitial = useRef(initialValue);
  const attach = useCallback((field: HTMLInputElement | null) => {
    if (!field || field === input.current) return;
    input.current = field;
    // The browser may have accepted keystrokes before React attached to the server HTML.
    if (field.value !== initialValue) {
      const draft = limitDraft(field.value);
      field.value = draft;
      setValue(draft);
      const video = parseYouTubeUrl(draft);
      setOpen(!video && document.activeElement === field);
      if (video) onVideo(video);
    }
  }, [initialValue, onVideo]);
  useLayoutEffect(() => {
    if (lastDomInitial.current !== initialValue && input.current) input.current.value = initialValue;
    lastDomInitial.current = initialValue;
  }, [initialValue]);
  const cache = useRef(new Map<string, { expires: number; items: WorkSuggestion[] }>());
  const listId = useId();
  // Restore URL/submitted values without replacing the focused input node.
  if (initialValue !== lastInitialValue) {
    setLastInitialValue(initialValue);
    setValue(initialValue);
    setInvalidLink(false);
    setOpen(false);
    setActiveSlug(null);
  }
  const query = value.trim();
  const suggestionsEnabled = open && !!query && !looksLikeLink(query);
  const loading = result.query !== query;
  const prepared = Object.hasOwn(starters, query) ? starters[query] : undefined;
  const compatible = loading && result.query && query.startsWith(result.query)
    ? result.items.filter(item => [item.title, item.composer].some(label => label.toLowerCase().includes(query.toLowerCase())))
    : [];
  const people = useMemo(() => onComposer && query && !looksLikeLink(query) ? matchComposers(query) : null, [onComposer, query]);
  const works = loading ? prepared ?? compatible : result.error ? prepared ?? [] : result.items;
  const items: Option[] = [...(people?.matches ?? []).map(person => ({
    slug: "composer:" + person.id, title: person.nameKo, person,
    composer: person.period === "other" ? "작곡가" : PERIOD_LABELS[person.period] + " 시대 작곡가",
  })), ...works];
  const visible = suggestionsEnabled && (!loading || items.length > 0);
  const active = items.findIndex(item => item.slug === activeSlug);

  useEffect(() => {
    if (visible && active >= 0) document.getElementById(`${listId}-${active}`)?.scrollIntoView?.({ block: "nearest" });
  }, [visible, active, listId]);

  useEffect(() => {
    const dismiss = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);

  useEffect(() => {
    if (!suggestionsEnabled) return;
    const controller = new AbortController();
    const cached = cache.current.get(query);
    const fresh = cached && cached.expires > Date.now();
    const timer = setTimeout(async () => {
      try {
        let suggestions = fresh ? cached.items : undefined;
        if (!suggestions) {
          const response = await fetch(`/api/catalog/suggest?${new URLSearchParams({ q: query })}`, { signal: controller.signal });
          if (!response.ok) throw new Error("Suggestions unavailable");
          suggestions = (await response.json()).suggestions as WorkSuggestion[];
        }
        if (controller.signal.aborted) return;
        cache.current.delete(query);
        cache.current.set(query, { expires: fresh ? cached.expires : Date.now() + 60_000, items: suggestions });
        if (cache.current.size > 20) cache.current.delete(cache.current.keys().next().value!);
        setResult({ query, items: suggestions, error: false });
      } catch {
        if (!controller.signal.aborted) setResult({ query, items: [], error: true });
      }
    }, fresh ? 0 : 100);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, suggestionsEnabled]);

  function clearCompositionState() {
    composingRef.current = false;
    setComposing(false);
  }
  function choose(work: Option) {
    clearCompositionState();
    if (work.person && onComposer) { setOpen(false); setActiveSlug(null); onComposer(work.person); return; }
    if (input.current) input.current.value = work.title;
    setValue(work.title); setOpen(false); setActiveSlug(null); onSelect(work);
  }
  function submit() {
    if (composingRef.current || !query) return;
    setOpen(false); setActiveSlug(null);
    const id = parseYouTubeUrl(query);
    if (id) onVideo(id, true);
    else if (looksLikeLink(query)) setInvalidLink(true);
    else if (people?.exact && onComposer) onComposer(people.exact);
    else onSubmit(query);
  }

  return (
    <div ref={root} className="relative w-full" onBlur={event => {
      if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
    }}>
      <form role="search" onSubmit={event => { event.preventDefault(); submit(); }}
        className="flex min-h-16 items-center gap-2 rounded-full border border-neutral-300 bg-white pr-3 pl-6 shadow-[0_2px_12px_0_rgb(0_0_0/0.04)] transition focus-within:border-neutral-500 sm:min-h-18 sm:gap-3 sm:pr-4 sm:pl-7">
        <div className="relative min-w-0 flex-1">
        <input ref={attach} role="combobox" aria-label={linkHint ? "유튜브 또는 유튜브 뮤직 영상 링크" : "곡명, 작곡가, 별칭 검색"}
          aria-invalid={invalidLink || undefined} aria-describedby={invalidLink ? listId + "-error" : undefined}
          aria-autocomplete="list" aria-expanded={visible} aria-controls={visible ? listId : undefined}
          aria-activedescendant={visible && active >= 0 && items[active] ? `${listId}-${active}` : undefined}
          autoComplete="off" inputMode={linkHint ? "url" : "search"} enterKeyHint="search" maxLength={2048} defaultValue={initialValue}
          placeholder={searchPlaceholder} className="block w-full min-w-0 bg-transparent py-5 text-base text-neutral-900 outline-none placeholder:text-transparent"
          onFocus={() => setOpen(true)} onChange={event => {
            const raw = event.target.value;
            const next = limitDraft(raw);
            if (raw !== next) event.target.value = next;
            const id = looksLikeLink(next) ? parseYouTubeUrl(next) : null;
            setValue(next); setActiveSlug(null); setOpen(!id); setInvalidLink(false);
            onVideo(id);
            if (!next.trim()) onClear();
          }}
          onCompositionStart={() => { composingRef.current = true; setComposing(true); }}
          onCompositionEnd={event => { clearCompositionState(); setValue(event.currentTarget.value); }}
          onKeyDown={event => {
            if (event.nativeEvent.isComposing || composingRef.current || event.keyCode === 229) {
              if (event.key === "Enter") event.preventDefault();
              return;
            }
            if (event.key === "Escape") { setOpen(false); setActiveSlug(null); }
            else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault(); setOpen(true);
              if (items.length) setActiveSlug(items[event.key === "ArrowDown" ? (active + 1) % items.length : (active <= 0 ? items.length - 1 : active - 1)].slug);
            } else if (event.key === "Enter") {
              event.preventDefault();
              if (visible && items[active]) choose(items[active]); else submit();
            }
          }} />
        {/* Fit the prompt independently so typed text stays at its readable size. */}
        {!value ? <SingleLineText aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 text-sm leading-5 text-neutral-400 sm:text-base sm:leading-6">{searchPlaceholder}</SingleLineText> : null}
        </div>
        {value ? <button type="button" className="icon-button size-8!" title="검색어 지우기" aria-label="검색어 지우기" onClick={() => {
          clearCompositionState();
          if (input.current) input.current.value = "";
          setValue(""); setInvalidLink(false); setActiveSlug(null); setOpen(false); onClear(); input.current?.focus();
        }}><X aria-hidden="true" className="size-4" /></button> : null}
        <button type="button" className="icon-button text-red-600! aria-pressed:bg-red-50" title="유튜브로 찾기" aria-label="유튜브로 찾기" aria-pressed={linkHint} onClick={() => {
          setLinkHint(!linkHint); clearCompositionState(); setInvalidLink(false);
          setOpen(false); setActiveSlug(null);
          input.current?.focus();
          if (value) input.current?.select();
        }}><Youtube aria-hidden="true" className="size-5" /></button>
        <button type="submit" disabled={!query || composing} title="검색" aria-label="검색" className="grid size-10 shrink-0 place-items-center rounded-full bg-neutral-900 text-white transition hover:bg-emerald-800 disabled:bg-neutral-100 disabled:text-neutral-400"><ArrowRight aria-hidden="true" className="size-5" /></button>
      </form>
      {invalidLink ? <p id={listId + "-error"} role="alert" className="mt-3 text-sm text-red-700">유튜브 또는 유튜브 뮤직의 개별 영상 링크를 입력해 주세요.</p> : null}
      {visible ? <div className="absolute inset-x-0 top-full z-30 mt-2 max-h-[min(26rem,50svh)] overflow-y-auto rounded-lg border border-neutral-200 bg-white p-1.5 shadow-lg">
        {!loading && result.error && !items.length ? <p role="alert" className="px-3 py-4 text-sm text-neutral-600">추천 작품을 불러오지 못했습니다.</p> : null}
        <ul id={listId} role="listbox" aria-label="작곡가 및 작품 추천">
          {items.map((work, index) => <li id={`${listId}-${index}`} key={work.slug} role="option" aria-selected={active === index}
            className={`flex cursor-pointer items-center gap-3 rounded-md px-3 py-3 ${active === index ? "bg-neutral-100" : "hover:bg-neutral-50"}`}
            onPointerMove={() => setActiveSlug(work.slug)} onPointerDown={event => event.preventDefault()} onClick={() => choose(work)}>
            {work.person && <span className="grid size-10 shrink-0 place-items-center overflow-hidden rounded-md bg-neutral-100 text-neutral-500">
              {work.person.portraitSrc ? <Image alt="" src={work.person.portraitSrc} width={40} height={40} className="size-full object-cover" /> : <UserRound className="size-5" aria-hidden="true" />}
            </span>}
            <div className="min-w-0 flex-1"><p className="break-words text-sm font-medium text-neutral-900">{work.title}</p><p className="mt-1 break-words text-xs text-neutral-500">{work.composer}</p></div>
            <ArrowUpLeft aria-hidden="true" className="size-4 shrink-0 text-neutral-400" />
          </li>)}
        </ul>
        {!result.error && !items.length ? <p role="status" className="px-3 py-4 text-sm text-neutral-500">추천 작품이 없습니다.</p> : null}
      </div> : null}
    </div>
  );
}
