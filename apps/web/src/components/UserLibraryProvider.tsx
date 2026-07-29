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
  type NotificationChannel,
  type NotificationPreferences,
  saveNotificationPreference,
  saveWatchedWork,
} from "@/lib/user-library";

import { useAuth } from "./AuthProvider";

type UserLibraryContextValue = {
  error: string | null;
  isPending: (workSlug: string) => boolean;
  isWatched: (workSlug: string) => boolean;
  loading: boolean;
  preferences: NotificationPreferences;
  setPreference: (channel: NotificationChannel, enabled: boolean) => Promise<void>;
  toggleWork: (workSlug: string) => Promise<void>;
  watchedSlugs: string[];
};

const UserLibraryContext = createContext<UserLibraryContextValue | null>(null);

const initialPreferences: NotificationPreferences = {
  email: true,
  web_push: false,
};
const emptyWatchedSlugs: string[] = [];

type LoadedLibrary = {
  error: string | null;
  preferences: NotificationPreferences;
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
  const { loading: authLoading, openAuth, user } = useAuth();
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

    if (!user || !client) {
      return () => {
        active = false;
      };
    }

    void loadUserLibrary(client, user.id)
      .then((snapshot) => {
        if (!active) return;
        setLibrary({
          error: null,
          preferences: snapshot.preferences,
          userId: user.id,
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
          preferences: initialPreferences,
          userId: user.id,
          watchedSlugs: [],
        });
      });

    return () => {
      active = false;
    };
  }, [client, user]);

  const hasLoadedLibrary = Boolean(user && library?.userId === user.id);
  const visibleWatchedSlugs = hasLoadedLibrary
    ? library!.watchedSlugs
    : emptyWatchedSlugs;
  const visiblePreferences = hasLoadedLibrary
    ? library!.preferences
    : initialPreferences;
  const visibleError = hasLoadedLibrary ? library!.error : null;

  const toggleWork = useCallback(
    async (workSlug: string) => {
      if (!user || !client) {
        if (!user) openAuth("signin");
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
    }, [client, openAuth, pendingItems, user, visibleWatchedSlugs],
  );

  const setPreference = useCallback(
    async (channel: NotificationChannel, enabled: boolean) => {
      if (!user || !client) {
        if (!user) openAuth("signin");
        return;
      }

      setLibrary((current) =>
        current?.userId === user.id ? { ...current, error: null } : current,
      );
      try {
        await saveNotificationPreference(client, user, channel, enabled);
        setLibrary((current) =>
          current?.userId === user.id
            ? {
                ...current,
                preferences: { ...current.preferences, [channel]: enabled },
              }
            : current,
        );
      } catch (saveError) {
        setLibrary((current) =>
          current?.userId === user.id
            ? {
                ...current,
                error:
                  saveError instanceof Error
                    ? saveError.message
                    : "알림 설정을 저장하지 못했습니다.",
              }
            : current,
        );
      }
    },
    [client, openAuth, user],
  );

  const value = useMemo<UserLibraryContextValue>(
    () => ({
      error: visibleError,
      isPending: (workSlug) =>
        Boolean(user && pendingItems.has(`${user.id}:${workSlug}`)),
      isWatched: (workSlug) => visibleWatchedSlugs.includes(workSlug),
      loading: authLoading || Boolean(user && client && !hasLoadedLibrary),
      preferences: visiblePreferences,
      setPreference,
      toggleWork,
      watchedSlugs: visibleWatchedSlugs,
    }),
    [
      authLoading,
      client,
      hasLoadedLibrary,
      pendingItems,
      setPreference,
      toggleWork,
      user,
      visibleError,
      visiblePreferences,
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
