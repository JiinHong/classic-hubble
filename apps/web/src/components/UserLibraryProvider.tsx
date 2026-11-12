"use client";

import type { SupabaseClient } from "@supabase/supabase-js";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  createSupabaseClient,
  isSupabaseConfigured,
} from "@/lib/supabase/client";
import {
  loadUserLibrary,
  saveWatchedWork,
} from "@/lib/user-library";

import { useAuth } from "./AuthProvider";

type UserLibraryContextValue = {
  error: string | null;
  isPending: (workSlug: string) => boolean;
  isWatched: (workSlug: string) => boolean;
  loading: boolean;
  toggleWork: (workSlug: string) => Promise<void>;
  watchedSlugs: string[];
};

const UserLibraryContext = createContext<UserLibraryContextValue | null>(null);

const emptyWatchedSlugs: string[] = [];

type LoadedLibrary = {
  error: string | null;
  userId: string;
  watchedSlugs: string[];
};

type UserLibraryProviderProps = {
  children: ReactNode;
  client?: SupabaseClient;
};

export function UserLibraryProvider({
  children,
  client: providedClient,
}: UserLibraryProviderProps) {
  const { loading: authLoading, signIn, user } = useAuth();
  const userId = user?.id;
  const client = useMemo(
    () =>
      providedClient ??
      (isSupabaseConfigured ? createSupabaseClient() : null),
    [providedClient],
  );
  const [library, setLibrary] = useState<LoadedLibrary | null>(null);
  const [pendingItems, setPendingItems] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    let active = true;

    if (!userId || !client) {
      return () => {
        active = false;
      };
    }

    void loadUserLibrary(client, userId)
      .then((snapshot) => {
        if (!active) return;
        setLibrary({
          error: null,
          userId,
          watchedSlugs: snapshot.watchedSlugs,
        });
      })
      .catch((loadError) => {
        if (!active) return;
        setLibrary({
          error:
            loadError instanceof Error
              ? loadError.message
              : "관심곡을 불러오지 못했습니다.",
          userId,
          watchedSlugs: [],
        });
      });

    return () => {
      active = false;
    };
  }, [client, userId]);

  const hasLoadedLibrary = Boolean(user && library?.userId === user.id);
  const visibleWatchedSlugs = hasLoadedLibrary
    ? library!.watchedSlugs
    : emptyWatchedSlugs;
  const visibleError = hasLoadedLibrary ? library!.error : null;

  const toggleWork = useCallback(
    async (workSlug: string) => {
      if (!user || !client) {
        if (!user) signIn();
        return;
      }
      const pendingKey = `${user.id}:${workSlug}`;
      if (pendingItems.has(pendingKey)) return;

      const watched = visibleWatchedSlugs.includes(workSlug);
      setPendingItems((current) => new Set(current).add(pendingKey));
      setLibrary((current) =>
        current?.userId === user.id ? { ...current, error: null } : current,
      );

      try {
        await saveWatchedWork(client, user, workSlug, !watched);
        setLibrary((current) => {
          if (current?.userId !== user.id) return current;
          return {
            ...current,
            watchedSlugs: watched
              ? current.watchedSlugs.filter((slug) => slug !== workSlug)
              : Array.from(new Set([...current.watchedSlugs, workSlug])),
          };
        });
      } catch (saveError) {
        setLibrary((current) =>
          current?.userId === user.id
            ? {
                ...current,
                error:
                  saveError instanceof Error
                    ? saveError.message
                    : "관심곡을 저장하지 못했습니다.",
              }
            : current,
        );
      } finally {
        setPendingItems((current) => {
          const next = new Set(current);
          next.delete(pendingKey);
          return next;
        });
      }
    }, [client, signIn, pendingItems, user, visibleWatchedSlugs],
  );

  const value = useMemo<UserLibraryContextValue>(
    () => ({
      error: visibleError,
      isPending: (workSlug) =>
        Boolean(user && pendingItems.has(`${user.id}:${workSlug}`)),
      isWatched: (workSlug) => visibleWatchedSlugs.includes(workSlug),
      loading: authLoading || Boolean(user && client && !hasLoadedLibrary),
      toggleWork,
      watchedSlugs: visibleWatchedSlugs,
    }),
    [
      authLoading,
      client,
      hasLoadedLibrary,
      pendingItems,
      toggleWork,
      user,
      visibleError,
      visibleWatchedSlugs,
    ],
  );

  return (
    <UserLibraryContext.Provider value={value}>
      {children}
    </UserLibraryContext.Provider>
  );
}

export function useUserLibrary() {
  const value = useContext(UserLibraryContext);
  if (!value) {
    throw new Error("useUserLibrary must be used inside UserLibraryProvider");
  }
  return value;
}
