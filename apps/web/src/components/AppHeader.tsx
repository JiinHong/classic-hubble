"use client";

import Link from "next/link";
import Image from "next/image";
import type { User } from "@supabase/supabase-js";
import { Bell, LibraryBig, LogOut, Menu, UserRound, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "./AuthProvider";

function googlePhoto(user: User) {
  const identity = user.identities?.find(({ provider }) => provider === "google")?.identity_data;
  for (const value of [identity?.picture, identity?.avatar_url, user.user_metadata?.picture, user.user_metadata?.avatar_url]) {
    if (typeof value === "string" && /^https:\/\/(?:[a-z0-9-]+\.)*googleusercontent\.com\//i.test(value)) return value;
  }
  return null;
}

function ProfileAvatar({ photo }: { photo: string | null }) {
  const [failed, setFailed] = useState(false);
  const style = "size-9 shrink-0 rounded-full";
  if (!photo || failed) return <span role="img" aria-label="내 프로필" className={`${style} grid place-items-center bg-neutral-100 text-neutral-600`}>
    <UserRound aria-hidden="true" className="size-5" />
  </span>;
  return <Image src={photo} alt="내 프로필" width={36} height={36} unoptimized referrerPolicy="no-referrer"
    className={`${style} bg-neutral-100 object-cover`} onError={() => setFailed(true)} />;
}

export function AppHeader() {
  const { loading, signIn, signOut, user } = useAuth();
  const photo = user ? googlePhoto(user) : null;
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const dismiss = (e: PointerEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);
  return <header className="relative z-40 bg-white">
    <div className="mx-auto flex h-18 max-w-[1440px] items-center justify-between gap-3 px-4 sm:px-8">
      <Link href="/" aria-label="클래식허블 홈" className="flex shrink-0 items-center text-neutral-900">
        <Image src="/brand/hubble-logo.png" alt="클래식허블" width={360} height={240} className="h-12 w-auto" priority unoptimized />
      </Link>
      <div className="flex items-center gap-2 sm:gap-3">
        <div ref={root} className="relative" onKeyDown={e => { if (e.key === "Escape") { setOpen(false); toggle.current?.focus(); } }} onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false); }}>
          <button ref={toggle} type="button" aria-label="메뉴" title="메뉴" aria-expanded={open} aria-controls="site-navigation" className="icon-button" onClick={() => setOpen(v => !v)}>
            {open ? <X className="size-5" aria-hidden="true" /> : <Menu className="size-5" aria-hidden="true" />}
          </button>
          {open ? <nav id="site-navigation" aria-label="보조 메뉴" className="absolute right-0 top-full mt-2 w-44 rounded-lg border border-neutral-200 bg-white p-1.5 shadow-lg">
            {[{ href: "/composers", label: "작곡가", icon: LibraryBig }, { href: "/watchlist", label: "관심곡", icon: Bell }].map(({ href, label, icon: Icon }) =>
              <Link key={href} href={href} aria-label={label} onClick={() => setOpen(false)} className="flex items-center gap-3 rounded-md px-3 py-3 text-sm text-neutral-700 hover:bg-neutral-50"><Icon className="size-4" aria-hidden="true" />{label}</Link>)}
          </nav> : null}
        </div>
        {user ? <div className="flex min-w-0 items-center gap-1">
          <ProfileAvatar key={user.id + ":" + photo} photo={photo} />
          <button type="button" className="icon-button" aria-label="로그아웃" title="로그아웃" onClick={() => void signOut()}><LogOut aria-hidden="true" className="size-4" /></button>
        </div> : <button type="button" aria-label="로그인" disabled={loading} onClick={() => signIn()} className="h-9 rounded-md bg-neutral-900 px-4 text-sm font-medium text-white hover:bg-neutral-700 disabled:opacity-40">로그인</button>}
      </div>
    </div>
  </header>;
}
