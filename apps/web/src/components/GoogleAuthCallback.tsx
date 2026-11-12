"use client";

import { useEffect, useRef } from "react";
import { callbackDestination, callbackPath, tabStorage, takeReturnPath } from "@/lib/google-auth";
import { createSupabaseClient, isSupabaseConfigured } from "@/lib/supabase/client";

export function GoogleAuthCallback() {
  const pending = useRef<Promise<string> | null>(null);
  useEffect(() => {
    let active = true;
    if (!pending.current) {
      const url = new URL(window.location.href);
      window.history.replaceState(window.history.state, "", callbackPath);
      const saved = takeReturnPath(url.origin, tabStorage());
      pending.current = callbackDestination(url, saved, isSupabaseConfigured
        ? code => createSupabaseClient().auth.exchangeCodeForSession(code) : null);
    }
    void pending.current.then(path => { if (active) window.location.replace(path); });
    return () => { active = false; };
  }, []);
  return <main className="mx-auto max-w-xl px-4 py-12"><p role="status">로그인 정보를 확인하고 있습니다.</p></main>;
}
