import type { SupabaseClient } from "@supabase/supabase-js";

export type NotificationChannel = "email" | "web_push";

export type NotificationPreferences = Record<NotificationChannel, boolean>;

export type UserLibrarySnapshot = {
  preferences: NotificationPreferences;
  watchedSlugs: string[];
};

export type LibraryUser = {
  email?: string | null;
  id: string;
};

type Relation<T> = T | T[] | null;

type WatchlistRow = {
  works: Relation<{ slug: string }>;
};

type PreferenceRow = {
  channel: NotificationChannel;
  enabled: boolean;
};

const defaultPreferences: NotificationPreferences = {
  email: true,
  web_push: false,
};

export async function loadUserLibrary(
  client: SupabaseClient,
  userId: string,
): Promise<UserLibrarySnapshot> {
  const [watchlistResult, preferencesResult] = await Promise.all([
    client.from("watchlist_items").select("works(slug)").eq("user_id", userId),
    client
      .from("notification_preferences")
      .select("channel, enabled")
      .eq("user_id", userId),
  ]);

  if (watchlistResult.error || preferencesResult.error) {
    throw new Error("관심곡 정보를 불러오지 못했습니다.");
  }

  const watchedSlugs = Array.from(
    new Set(
      ((watchlistResult.data ?? []) as unknown as WatchlistRow[])
        .map((row) => firstRelation(row.works)?.slug)
        .filter((slug): slug is string => Boolean(slug)),
    ),
  );
  const preferences = { ...defaultPreferences };

  for (const row of (preferencesResult.data ?? []) as unknown as PreferenceRow[]) {
    preferences[row.channel] = row.enabled;
  }

  return { preferences, watchedSlugs };
}

export async function saveWatchedWork(
  client: SupabaseClient,
  user: LibraryUser,
  workSlug: string,
  watched: boolean,
) {
  if (watched) {
    await ensureProfile(client, user);
  }

  const workId = await findWorkId(client, workSlug);
  if (!workId) {
    throw new Error("작품 정보를 찾을 수 없습니다.");
  }

  const result = watched
    ? await client.from("watchlist_items").upsert(
        { user_id: user.id, work_id: workId },
        { ignoreDuplicates: true, onConflict: "user_id,work_id" },
      )
    : await client
        .from("watchlist_items")
        .delete()
        .eq("user_id", user.id)
        .eq("work_id", workId);

  if (result.error) {
    throw new Error(watched ? "관심곡을 저장하지 못했습니다." : "관심곡을 해제하지 못했습니다.");
  }
}

export async function saveNotificationPreference(
  client: SupabaseClient,
  user: LibraryUser,
  channel: NotificationChannel,
  enabled: boolean,
) {
  await ensureProfile(client, user);
  const { error } = await client.from("notification_preferences").upsert(
    { channel, enabled, user_id: user.id },
    { onConflict: "user_id,channel" },
  );

  if (error) {
    throw new Error("알림 설정을 저장하지 못했습니다.");
  }
}

async function ensureProfile(client: SupabaseClient, user: LibraryUser) {
  const { error } = await client.from("profiles").upsert(
    { email: user.email ?? null, id: user.id },
    { ignoreDuplicates: true, onConflict: "id" },
  );

  if (error) {
    throw new Error("사용자 정보를 준비하지 못했습니다.");
  }
}

async function findWorkId(client: SupabaseClient, workSlug: string) {
  const { data, error } = await client
    .from("works")
    .select("id")
    .eq("slug", workSlug)
    .limit(1);

  if (error) {
    throw new Error("작품 정보를 확인하지 못했습니다.");
  }

  return (data?.[0] as { id?: string } | undefined)?.id ?? null;
}

function firstRelation<T>(value: Relation<T>) {
  if (Array.isArray(value)) return value[0] ?? null;
  return value;
}
