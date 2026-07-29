import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createSupabaseClient: vi.fn(),
}));

vi.mock("@/lib/supabase/client", () => ({
  createSupabaseClient: mocks.createSupabaseClient,
  isSupabaseConfigured: false,
}));

import { AuthProvider, useAuth } from "./AuthProvider";
import { UserLibraryProvider, useUserLibrary } from "./UserLibraryProvider";

function AppShellProbe() {
  const auth = useAuth();
  const library = useUserLibrary();
  const [mutationStatus, setMutationStatus] = useState("idle");

  async function runAnonymousMutations() {
    try {
      auth.openAuth("signin");
      await auth.signOut();
      await library.toggleWork("beethoven-symphony-5");
      await library.setPreference("email", false);
      setMutationStatus("resolved");
    } catch {
      setMutationStatus("rejected");
    }
  }

  return (
    <>
      <p>fallback shell child</p>
      <output data-testid="auth-loading">{String(auth.loading)}</output>
      <output data-testid="library-loading">{String(library.loading)}</output>
      <output data-testid="library-defaults">
        {[
          library.watchedSlugs.length,
          library.preferences.email,
          library.preferences.web_push,
          library.isWatched("beethoven-symphony-5"),
          library.isPending("beethoven-symphony-5"),
        ].join(",")}
      </output>
      <button onClick={() => void runAnonymousMutations()} type="button">
        익명 동작 실행
      </button>
      <output>{mutationStatus}</output>
    </>
  );
}

describe("app provider stack without Supabase", () => {
  beforeEach(() => {
    mocks.createSupabaseClient.mockReset();
    mocks.createSupabaseClient.mockImplementation(() => {
      throw new Error("createSupabaseClient must not be called");
    });
  });

  it("renders children with resolved anonymous defaults and no-op mutations", async () => {
    render(
      <AuthProvider>
        <UserLibraryProvider>
          <AppShellProbe />
        </UserLibraryProvider>
      </AuthProvider>,
    );

    expect(screen.getByText("fallback shell child")).toBeTruthy();
    expect(screen.getByTestId("auth-loading").textContent).toBe("false");
    expect(screen.getByTestId("library-loading").textContent).toBe("false");
    expect(screen.getByTestId("library-defaults").textContent).toBe(
      "0,true,false,false,false",
    );

    fireEvent.click(screen.getByRole("button", { name: "익명 동작 실행" }));

    expect(await screen.findByText("resolved")).toBeTruthy();
    expect(mocks.createSupabaseClient).not.toHaveBeenCalled();
  });
});
