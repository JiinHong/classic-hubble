import { createClient, type Session, type SupabaseClient } from "@supabase/supabase-js";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider } from "./AuthProvider";
import { UserLibraryProvider } from "./UserLibraryProvider";
import { WatchlistButton } from "./WatchlistButton";

function createAuthClient(session: Session | null) {
  return {
    auth: {
      async getSession() {
        return { data: { session }, error: null };
      },
      onAuthStateChange() {
        return { data: { subscription: { unsubscribe: () => undefined } } };
      },
      signInWithOAuth: vi.fn(async () => ({ error: null })),
      signOut: vi.fn(async () => ({ error: null })),
    },
  } as unknown as SupabaseClient;
}

function createLibraryClient(requests: Request[]) {
  const customFetch: typeof fetch = async (input, init) => {
    const request = new Request(input, init);
    requests.push(request.clone());
    const path = new URL(request.url).pathname;

    if (path.endsWith("/watchlist_items") && request.method === "GET") {
      return Response.json([]);
    }
    if (path.endsWith("/notification_preferences") && request.method === "GET") {
      return Response.json([]);
    }
    if (path.endsWith("/works")) {
      return Response.json([{ id: "work-1" }]);
    }
    return new Response(null, { status: 201 });
  };

  return createClient("https://example.supabase.co", "sb_publishable_test", {
    auth: {
      autoRefreshToken: false,
      detectSessionInUrl: false,
      persistSession: false,
      storage: {
        async getItem() {
          return null;
        },
        async removeItem() {},
        async setItem() {},
      },
    },
    global: { fetch: customFetch },
  });
}

describe("WatchlistButton", () => {
  it("stores a work for the signed-in user and updates its state", async () => {
    const requests: Request[] = [];
    const session = {
      user: { email: "member@example.com", id: "user-1" },
    } as Session;

    render(
      <AuthProvider client={createAuthClient(session)}>
        <UserLibraryProvider client={createLibraryClient(requests)}>
          <WatchlistButton workSlug="beethoven-symphony-5" />
        </UserLibraryProvider>
      </AuthProvider>,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "이 곡 알림 받기" }),
    );

    expect(await screen.findByRole("button", { name: "알림 받는 중" })).toBeTruthy();
    expect(
      requests.some(
        (request) =>
          request.method === "POST" &&
          new URL(request.url).pathname.endsWith("/watchlist_items"),
      ),
    ).toBe(true);
  });

  it("opens authentication instead of writing for an anonymous visitor", async () => {
    const requests: Request[] = [];
    const client = createAuthClient(null);
    render(
      <AuthProvider client={client}>
        <UserLibraryProvider client={createLibraryClient(requests)}>
          <WatchlistButton workSlug="beethoven-symphony-5" />
        </UserLibraryProvider>
      </AuthProvider>,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "이 곡 알림 받기" }),
    );

    expect(client.auth.signInWithOAuth).toHaveBeenCalledOnce();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(requests).toHaveLength(0);
  });
});
