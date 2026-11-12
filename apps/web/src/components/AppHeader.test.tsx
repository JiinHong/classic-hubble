import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { Session, SupabaseClient } from "@supabase/supabase-js";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "./AppHeader";
import { AuthProvider } from "./AuthProvider";

function createClient(session: Session | null) {
  const signOut = vi.fn(async () => ({ error: null }));
  const client = {
    auth: {
      async getSession() {
        return { data: { session }, error: null };
      },
      onAuthStateChange() {
        return {
          data: { subscription: { unsubscribe: () => undefined } },
        };
      },
      signInWithOAuth: vi.fn(async () => ({ error: null })),
      signOut,
    },
  } as unknown as SupabaseClient;

  return { client, signOut };
}

describe("AppHeader authentication", () => {
  it.each([false, true])("places home immediately before composers in the main navigation (signed in: %s)", async (signedIn) => {
    const { client } = createClient(signedIn ? { user: { id: "u" } } as Session : null);
    render(<AuthProvider client={client}><AppHeader /></AuthProvider>);
    const nav = within(screen.getByRole("navigation", { name: "주요 메뉴" }));
    if (signedIn) await nav.findByRole("link", { name: "내 관심곡" });
    else await waitFor(() => expect(nav.getByRole("button", { name: "로그인" }).hasAttribute("disabled")).toBe(false));
    const home = nav.getByRole("link", { name: "홈", exact: true });
    expect(home.getAttribute("href")).toBe("/");
    expect(nav.getAllByRole("link").slice(0, 2)).toEqual([home, nav.getByRole("link", { name: "작곡가" })]);
  });

  it("uses the Hubble logo without a separate wordmark as the accessible home link", async () => {
    const { client } = createClient(null);
    render(<AuthProvider client={client}><AppHeader /></AuthProvider>);
    await waitFor(() => expect(screen.getByRole("button", { name: "로그인" }).hasAttribute("disabled")).toBe(false));
    const home = screen.getByRole("link", { name: "클래식허블 홈" });
    const logo = screen.getByRole("img", { name: "클래식허블" });
    expect(home.contains(logo)).toBe(true);
    expect(screen.queryByText("Classic Hubble", { exact: true })).toBeNull();
    expect(home.getAttribute("href")).toBe("/");
    expect(logo.getAttribute("src")).toBe("/brand/hubble-logo.png");
    expect(logo.getAttribute("width")).toBe("360");
    expect(logo.getAttribute("height")).toBe("240");
    expect(home.querySelector(".lucide-headphones")).toBeNull();
  });

  it("shows a direct composers link without a hamburger or a guest watchlist shortcut", async () => {
    const { client } = createClient(null);
    render(
      <AuthProvider client={client}>
        <AppHeader />
      </AuthProvider>,
    );

    expect(screen.queryByRole("link", { name: "검수" })).toBeNull();
    expect(screen.queryByRole("link", { name: "탐색" })).toBeNull();
    expect(screen.queryByRole("button", { name: "메뉴" })).toBeNull();
    expect(screen.queryByRole("link", { name: /관심곡/ })).toBeNull();
    expect(screen.getByRole("link", { name: "작곡가" }).getAttribute("href")).toBe(
      "/composers",
    );
    expect(
      screen.getByRole("link", { name: "클래식허블 홈" }).getAttribute(
        "aria-label",
      ),
    ).toBe("클래식허블 홈");
  });

  it("only starts Google from the welcome dialog and ignores a second submit", async () => {
    const { client } = createClient(null);
    render(
      <AuthProvider client={client}>
        <AppHeader />
      </AuthProvider>,
    );

    const loginButton = await screen.findByRole("button", { name: "로그인" });
    await waitFor(() => expect(loginButton.hasAttribute("disabled")).toBe(false));
    fireEvent.click(loginButton);
    expect(client.auth.signInWithOAuth).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog", { name: "클래식허블 로그인" })).toBeTruthy();
    expect(screen.queryByText("만나서 반가워요")).toBeNull();

    const google = screen.getByRole("button", { name: "Google로 계속하기" });
    fireEvent.click(google);
    fireEvent.click(google);
    expect(client.auth.signInWithOAuth).toHaveBeenCalledExactlyOnceWith({
      provider: "google", options: { redirectTo: window.location.origin + "/auth/callback" },
    });
  });

  it("can dismiss the welcome dialog without starting sign-in", async () => {
    const { client } = createClient(null);
    render(<AuthProvider client={client}><AppHeader /></AuthProvider>);
    const login = screen.getByRole("button", { name: "로그인" });
    await waitFor(() => expect(login.hasAttribute("disabled")).toBe(false));
    login.focus();
    fireEvent.click(login);
    const close = screen.getByRole("button", { name: "닫기" });
    close.focus();
    fireEvent.click(close);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.auth.signInWithOAuth).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(login);
  });

  it("allows retry after a failed sign-in start without displaying raw errors", async () => {
    const { client } = createClient(null);
    vi.mocked(client.auth.signInWithOAuth).mockRejectedValueOnce(new Error("private-detail"));
    render(<AuthProvider client={client}><AppHeader /></AuthProvider>);
    const login = screen.getByRole("button", { name: "로그인" });
    await waitFor(() => expect(login.hasAttribute("disabled")).toBe(false));
    fireEvent.click(login);
    fireEvent.click(screen.getByRole("button", { name: "Google로 계속하기" }));
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).not.toContain("private-detail");
    fireEvent.click(screen.getByRole("button", { name: "Google로 계속하기" }));
    expect(client.auth.signInWithOAuth).toHaveBeenCalledTimes(2);
  });

  it("shows the Google profile photo instead of the email and still signs out", async () => {
    const picture = "https://lh3.googleusercontent.com/a/example";
    const session = {
      user: { email: "member@example.com", id: "user-1", user_metadata: { picture } },
    } as Session;
    const { client, signOut } = createClient(session);
    render(
      <AuthProvider client={client}>
        <AppHeader />
      </AuthProvider>,
    );

    const avatar = await screen.findByRole("img", { name: "내 프로필" });
    const watchlist = screen.getByRole("link", { name: "내 관심곡" });
    expect(watchlist.getAttribute("href")).toBe("/watchlist");
    expect(watchlist.contains(avatar)).toBe(true);
    expect(screen.getAllByRole("link", { name: /관심곡/ })).toHaveLength(1);
    expect(screen.queryByText("관심곡")).toBeNull();
    expect(screen.getByRole("link", { name: "작곡가" }).getAttribute("href")).toBe("/composers");
    expect(avatar.getAttribute("src")).toBe(picture);
    expect(screen.queryByText("member@example.com")).toBeNull();
    fireEvent.error(avatar);
    expect(screen.getByRole("img", { name: "내 프로필" }).tagName).not.toBe("IMG");
    fireEvent.click(screen.getByRole("button", { name: "로그아웃" }));

    await waitFor(() => expect(signOut).toHaveBeenCalledOnce());
  });

  it.each([undefined, "https://googleusercontent.com.example.test/photo"])("uses a neutral avatar for an absent or non-Google photo (%s)", async (picture) => {
    const { client } = createClient({ user: { id: "u", email: "hidden@example.com", user_metadata: { picture } } } as Session);
    render(<AuthProvider client={client}><AppHeader /></AuthProvider>);
    const avatar = await screen.findByRole("img", { name: "내 프로필" });
    expect(avatar.tagName).not.toBe("IMG");
    expect(screen.getByRole("link", { name: "내 관심곡" }).contains(avatar)).toBe(true);
    expect(screen.queryByText("hidden@example.com")).toBeNull();
  });

  it("prefers the linked Google identity photo over stale account metadata", async () => {
    const picture = "https://lh3.googleusercontent.com/a/current";
    const { client } = createClient({ user: {
      id: "u", user_metadata: { avatar_url: "https://lh3.googleusercontent.com/a/old" },
      identities: [{ provider: "google", identity_data: { picture } }],
    } } as Session);
    render(<AuthProvider client={client}><AppHeader /></AuthProvider>);
    expect((await screen.findByRole("img", { name: "내 프로필" })).getAttribute("src")).toBe(picture);
  });
});
