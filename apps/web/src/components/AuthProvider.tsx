"use client";

import type { Session, SupabaseClient, User } from "@supabase/supabase-js";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { callbackPath, saveReturnPath, tabStorage } from "@/lib/google-auth";
import {
  createSupabaseClient,
  isSupabaseConfigured,
} from "@/lib/supabase/client";

type AuthContextValue = {
  loading: boolean;
  signIn: () => Promise<void>;
  session: Session | null;
  signOut: () => Promise<void>;
  user: User | null;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: ReactNode;
  client?: SupabaseClient;
};

export function AuthProvider({ children, client: providedClient }: AuthProviderProps) {
  const client = useMemo(
    () =>
      providedClient ??
      (isSupabaseConfigured ? createSupabaseClient() : null),
    [providedClient],
  );
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(() => Boolean(client));
  const [redirecting, setRedirecting] = useState(false);
  const starting = useRef(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const url = new URL(window.location.href);
    const reason = url.searchParams.get("auth_notice");
    if (url.pathname !== callbackPath && (reason === "failed" || reason === "cancelled")) {
      url.searchParams.delete("auth_notice");
      window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
      queueMicrotask(() => setNotice(reason === "cancelled" ? "Google 로그인이 취소되었습니다." : "Google 로그인을 완료하지 못했습니다."));
    }
    const restore = (event: PageTransitionEvent) => {
      if (event.persisted) { starting.current = false; setRedirecting(false); }
    };
    window.addEventListener("pageshow", restore);
    return () => window.removeEventListener("pageshow", restore);
  }, []);

  const signIn = useCallback(async () => {
    if (starting.current || window.location.pathname === callbackPath) return;
    if (!client) { setNotice("현재 Google 로그인을 사용할 수 없습니다."); return; }
    starting.current = true;
    setRedirecting(true);
    setNotice(null);
    const { origin, pathname, search } = window.location;
    saveReturnPath(pathname + search, origin, tabStorage());
    try {
      const { error } = await client.auth.signInWithOAuth({
        provider: "google", options: { redirectTo: origin + callbackPath },
      });
      if (error) throw error;
    } catch {
      starting.current = false;
      setRedirecting(false);
      setNotice("Google 로그인을 시작하지 못했습니다.");
    }
  }, [client]);

  useEffect(() => {
    if (!client) return;

    let active = true;

    void client.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session);
      setLoading(false);
    });

    const { data } = client.auth.onAuthStateChange((_event, nextSession) => {
      if (!active) return;
      setSession(nextSession);
      setLoading(false);
    });

    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, [client]);

  const value = useMemo<AuthContextValue>(
    () => ({
      loading: loading || redirecting,
      signIn,
      session,
      async signOut() {
        if (!client) return;
        const { error } = await client.auth.signOut();
        if (!error) setSession(null);
      },
      user: session?.user ?? null,
    }),
    [client, loading, redirecting, session, signIn],
  );

  return (
    <AuthContext.Provider value={value}>
      {notice && <div role="alert" className="flex flex-wrap items-center justify-center gap-3 bg-neutral-100 px-4 py-2 text-sm">
        {notice}
        <button type="button" className="underline" onClick={() => void signIn()}>다시 시도</button>
        <button type="button" onClick={() => setNotice(null)}>닫기</button>
      </div>}
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
