import { performances, works } from "@classic-hubble/shared";
import { createClient, type Session, type SupabaseClient } from "@supabase/supabase-js";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider } from "./AuthProvider";
import { UserLibraryProvider } from "./UserLibraryProvider";
import { WatchlistExperience } from "./WatchlistExperience";

function createAuthClient(session: Session | null) {
  return {
    auth: {
      async getSession() {
        return { data: { session }, error: null };
      },
      onAuthStateChange() {
        return { data: { subscription: { unsubscribe: () => undefined } } };
      },
      signInWithPassword: vi.fn(),
      signOut: vi.fn(async () => ({ error: null })),
      signUp: vi.fn(),
    },
  } as unknown as SupabaseClient;
}

function createLibraryClient(watchedSlugs: string[]) {
  const customFetch: typeof fetch = async (input, init) => {
    const request = new Request(input, init);
    const path = new URL(request.url).pathname;

    if (path.endsWith("/watchlist_items") && request.method === "GET") {
      return Response.json(watchedSlugs.map((slug) => ({ works: { slug } })));
    }
    if (path.endsWith("/notification_preferences") && request.method === "GET") {
      return Response.json([{ channel: "email", enabled: true }]);
    }
    return new Response(null, { status: 201 });
  };

  return createClient("https://example.supabase.co", "sb_publishable_test", {
    auth: {
      autoRefreshToken: false,
      detectSessionInUrl: false,
      persistSession: false,
    },
    global: { fetch: customFetch },
  });
}

describe("WatchlistExperience", () => {
  it("shows only the signed-in user's watched works and matching performances", async () => {
    const session = {
      user: { email: "member@example.com", id: "user-1" },
    } as Session;

    render(
      <AuthProvider client={createAuthClient(session)}>
        <UserLibraryProvider
          client={createLibraryClient(["rachmaninoff-piano-concerto-2"])}
        >
          <WatchlistExperience performances={performances} works={works} />
        </UserLibraryProvider>
      </AuthProvider>,
    );

    expect(
      await screen.findByRole("link", { name: /피아노 협주곡 2번/ }),
    ).toBeTruthy();
    expect(screen.queryByRole("link", { name: /교향곡 5번/ })).toBeNull();
    expect(await screen.findByText("김정원과 친구들 - 저먼 로맨틱스")).toBeTruthy();
  });

  it("shows a login prompt without placeholder works for an anonymous visitor", async () => {
    render(
      <AuthProvider client={createAuthClient(null)}>
        <UserLibraryProvider client={createLibraryClient([])}>
          <WatchlistExperience performances={performances} works={works} />
        </UserLibraryProvider>
      </AuthProvider>,
    );

    expect(await screen.findByRole("button", { name: "로그인" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: /피아노 협주곡 2번/ })).toBeNull();
  });
});
