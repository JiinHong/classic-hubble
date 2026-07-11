"use client";

import type { Session, SupabaseClient, User } from "@supabase/supabase-js";
import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { AuthMode } from "@/lib/auth";
import { createSupabaseClient } from "@/lib/supabase/client";

import { AuthDialog } from "./AuthDialog";

type AuthContextValue = {
  loading: boolean;
  openAuth: (mode?: AuthMode) => void;
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
    () => providedClient ?? createSupabaseClient(),
    [providedClient],
  );
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<AuthMode>("signin");

  useEffect(() => {
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
      loading,
      openAuth(mode = "signin") {
        setDialogMode(mode);
        setDialogOpen(true);
      },
      session,
      async signOut() {
        const { error } = await client.auth.signOut();
        if (!error) setSession(null);
      },
      user: session?.user ?? null,
    }),
    [client, loading, session],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
      {dialogOpen ? (
        <AuthDialog
          auth={client.auth}
          initialMode={dialogMode}
          key={dialogMode}
          onAuthenticated={() => setDialogOpen(false)}
          onClose={() => setDialogOpen(false)}
          open
          redirectUrl={
            typeof window === "undefined" ? "/" : `${window.location.origin}/`
          }
        />
      ) : null}
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
