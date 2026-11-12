"use client";

import Link from "next/link";
import Image from "next/image";
import type { User } from "@supabase/supabase-js";
import { LibraryBig, LogOut, UserRound } from "lucide-react";
import { useState } from "react";
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
  return <header className="relative z-40 bg-white">
    <div className="mx-auto flex h-18 max-w-[1440px] items-center justify-between gap-3 px-4 sm:px-8">
      <Link href="/" aria-label="클래식허블 홈" className="flex shrink-0 items-center text-neutral-900">
        <Image src="/brand/hubble-logo.png" alt="클래식허블" width={360} height={240} className="h-12 w-auto" priority unoptimized />
      </Link>
      <nav aria-label="주요 메뉴" className="flex items-center gap-1 sm:gap-2">
        <Link href="/composers" prefetch={false} className="inline-flex h-11 items-center gap-2 whitespace-nowrap rounded-md px-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 hover:text-neutral-950">
          <LibraryBig aria-hidden="true" className="size-4" />
          작곡가
        </Link>
        {user ? <>
          <Link href="/watchlist" aria-label="내 관심곡" title="내 관심곡" className="grid size-11 shrink-0 place-items-center rounded-full hover:bg-neutral-100">
            <ProfileAvatar key={user.id + ":" + photo} photo={photo} />
          </Link>
          <button type="button" className="icon-button" aria-label="로그아웃" title="로그아웃" onClick={() => void signOut()}><LogOut aria-hidden="true" className="size-4" /></button>
        </> : <button type="button" aria-label="로그인" disabled={loading} onClick={() => signIn()} className="h-9 rounded-md bg-neutral-900 px-4 text-sm font-medium text-white hover:bg-neutral-700 disabled:opacity-40">로그인</button>}
      </nav>
    </div>
  </header>;
}
