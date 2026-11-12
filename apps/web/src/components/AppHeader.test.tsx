import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

  it("keeps secondary navigation accessible without exposing review or dashboard links", async () => {
    const { client } = createClient(null);
    render(
      <AuthProvider client={client}>
        <AppHeader />
      </AuthProvider>,
    );

    expect(screen.queryByRole("link", { name: "검수" })).toBeNull();
    expect(screen.queryByRole("link", { name: "탐색" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "메뉴" }));
    expect(screen.getByRole("link", { name: "작곡가" }).getAttribute("href")).toBe(
      "/composers",
    );
    expect(
      screen.getByRole("link", { name: "클래식허블 홈" }).getAttribute(
        "aria-label",
      ),
    ).toBe("클래식허블 홈");
  });

  it("starts Google directly and ignores a second click during navigation", async () => {
    const { client } = createClient(null);
    render(
      <AuthProvider client={client}>
        <AppHeader />
      </AuthProvider>,
    );

    const loginButton = await screen.findByRole("button", { name: "로그인" });
    await waitFor(() => expect(loginButton.hasAttribute("disabled")).toBe(false));
    fireEvent.click(loginButton);

    fireEvent.click(loginButton);
    expect(client.auth.signInWithOAuth).toHaveBeenCalledExactlyOnceWith({
      provider: "google", options: { redirectTo: window.location.origin + "/auth/callback" },
    });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("allows retry after a failed sign-in start without displaying raw errors", async () => {
    const { client } = createClient(null);
    vi.mocked(client.auth.signInWithOAuth).mockRejectedValueOnce(new Error("private-detail"));
    render(<AuthProvider client={client}><AppHeader /></AuthProvider>);
    const login = screen.getByRole("button", { name: "로그인" });
    await waitFor(() => expect(login.hasAttribute("disabled")).toBe(false));
    fireEvent.click(login);
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).not.toContain("private-detail");
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(client.auth.signInWithOAuth).toHaveBeenCalledTimes(2);
  });

  it("shows the signed-in email and signs out", async () => {
    const session = {
      user: { email: "member@example.com", id: "user-1" },
    } as Session;
    const { client, signOut } = createClient(session);
    render(
      <AuthProvider client={client}>
        <AppHeader />
      </AuthProvider>,
    );

    expect(await screen.findByText("member@example.com")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "로그아웃" }));

    await waitFor(() => expect(signOut).toHaveBeenCalledOnce());
  });
});
