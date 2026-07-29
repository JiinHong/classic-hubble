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
      signInWithPassword: vi.fn(),
      signOut,
      signUp: vi.fn(),
    },
  } as unknown as SupabaseClient;

  return { client, signOut };
}

describe("AppHeader authentication", () => {
  it("keeps icon-only mobile navigation links named", async () => {
    const { client } = createClient(null);
    render(
      <AuthProvider client={client}>
        <AppHeader />
      </AuthProvider>,
    );

    expect(
      (await screen.findByRole("link", { name: "탐색" })).getAttribute(
        "aria-label",
      ),
    ).toBe("탐색");
    expect(screen.getByRole("link", { name: "작곡가" }).getAttribute("href")).toBe(
      "/composers",
    );
    expect(
      screen.getByRole("link", { name: "클래식허블 홈" }).getAttribute(
        "aria-label",
      ),
    ).toBe("클래식허블 홈");
  });

  it("opens the login dialog for an anonymous visitor", async () => {
    const { client } = createClient(null);
    render(
      <AuthProvider client={client}>
        <AppHeader />
      </AuthProvider>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "로그인" }));

    expect(await screen.findByRole("dialog")).toBeTruthy();
    expect(screen.getByLabelText("이메일")).toBeTruthy();
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
