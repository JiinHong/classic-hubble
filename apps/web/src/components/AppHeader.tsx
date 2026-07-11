"use client";

import Link from "next/link";
import { Bell, Headphones, LogIn, LogOut, Search, Settings2, UserRound } from "lucide-react";

import { useAuth } from "./AuthProvider";

const navigation = [
  { href: "/", label: "탐색", icon: Search },
  { href: "/watchlist", label: "관심곡", icon: Bell },
  { href: "/admin/review", label: "검수", icon: Settings2 },
];

export function AppHeader() {
  const { loading, openAuth, signOut, user } = useAuth();

  return (
    <header className="sticky top-0 z-20 border-b border-stone-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link
          aria-label="클래식허블 홈"
          className="flex items-center gap-2 text-stone-950"
          href="/"
        >
          <span className="grid size-9 place-items-center rounded-md bg-stone-950 text-white">
            <Headphones aria-hidden="true" className="size-5" />
          </span>
          <span className="hidden text-lg font-black tracking-normal sm:inline">
            클래식허블
          </span>
        </Link>

        <div className="flex min-w-0 items-center gap-2">
          <nav className="flex items-center gap-1">
            {navigation.map((item) => {
              const Icon = item.icon;

              return (
                <Link
                  aria-label={item.label}
                  key={item.href}
                  href={item.href}
                  className="inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm font-semibold text-stone-600 transition hover:bg-stone-100 hover:text-stone-950"
                >
                  <Icon aria-hidden="true" className="size-4" />
                  <span className="hidden sm:inline">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <span aria-hidden="true" className="h-6 w-px bg-stone-200" />

          {user ? (
            <div className="flex min-w-0 items-center gap-1">
              <span className="hidden max-w-44 items-center gap-2 truncate px-2 text-sm font-bold text-stone-600 md:inline-flex">
                <UserRound aria-hidden="true" className="size-4 shrink-0 text-emerald-700" />
                <span className="truncate">{user.email}</span>
              </span>
              <button
                aria-label="로그아웃"
                className="grid size-10 place-items-center rounded-md text-stone-500 transition hover:bg-stone-100 hover:text-stone-950"
                onClick={() => void signOut()}
                title="로그아웃"
                type="button"
              >
                <LogOut aria-hidden="true" className="size-4" />
              </button>
            </div>
          ) : (
            <button
              aria-label="로그인"
              className="inline-flex h-10 items-center gap-2 rounded-md bg-stone-950 px-3 text-sm font-black text-white transition hover:bg-emerald-800 disabled:opacity-45"
              disabled={loading}
              onClick={() => openAuth("signin")}
              type="button"
            >
              <LogIn aria-hidden="true" className="size-4" />
              <span aria-hidden="true" className="hidden sm:inline">로그인</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
