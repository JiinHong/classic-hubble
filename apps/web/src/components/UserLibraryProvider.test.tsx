import type { Session, SupabaseClient } from "@supabase/supabase-js";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  loadUserLibrary,
  saveNotificationPreference,
  saveWatchedWork,
} from "@/lib/user-library";

import { AuthProvider } from "./AuthProvider";
import { UserLibraryProvider, useUserLibrary } from "./UserLibraryProvider";

vi.mock("@/lib/user-library", () => ({
  loadUserLibrary: vi.fn(),
  saveNotificationPreference: vi.fn(),
  saveWatchedWork: vi.fn(),
}));

function createAuthHarness(initialSession: Session) {
  let listener: ((event: string, session: Session | null) => void) | null =
    null;
  const client = {
    auth: {
      async getSession() {
        return { data: { session: initialSession }, error: null };
      },
      onAuthStateChange(nextListener: typeof listener) {
        listener = nextListener;
        return { data: { subscription: { unsubscribe: () => undefined } } };
      },
      signOut: vi.fn(async () => ({ error: null })),
    },
  } as unknown as SupabaseClient;

  return {
    client,
    emit(session: Session | null) {
      listener?.("SIGNED_IN", session);
    },
  };
}

function sessionFor(id: string) {
  return { user: { email: `${id}@example.com`, id } } as Session;
}

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

function LibraryProbe() {
  const { loading, toggleWork, watchedSlugs } = useUserLibrary();

  return (
    <>
      <output data-testid="watched-slugs">{watchedSlugs.join(",")}</output>
      <button
        disabled={loading}
        onClick={() => void toggleWork("a-work")}
        type="button"
      >
        A 작품 저장
      </button>
    </>
  );
}

describe("UserLibraryProvider session isolation", () => {
  beforeEach(() => {
    vi.mocked(loadUserLibrary).mockReset();
    vi.mocked(saveWatchedWork).mockReset();
    vi.mocked(saveNotificationPreference).mockReset();
  });

  it("does not reload the library when the same user's session is refreshed", async () => {
    const auth = createAuthHarness(sessionFor("user-a"));
    const client = {} as SupabaseClient;
    vi.mocked(loadUserLibrary).mockResolvedValue({
      preferences: { email: true, web_push: false },
      watchedSlugs: ["a-work"],
    });
    render(
      <AuthProvider client={auth.client}>
        <UserLibraryProvider client={client}>
          <LibraryProbe />
        </UserLibraryProvider>
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("watched-slugs").textContent).toBe("a-work"),
    );
    await act(async () => auth.emit(sessionFor("user-a")));
    expect(loadUserLibrary).toHaveBeenCalledTimes(1);
  });

  it("ignores a previous user's mutation after the active session changes", async () => {
    const pendingSave = deferred();
    const auth = createAuthHarness(sessionFor("user-a"));
    vi.mocked(loadUserLibrary).mockImplementation(async (_client, userId) => ({
      preferences: { email: true, web_push: false },
      watchedSlugs: userId === "user-b" ? ["b-work"] : [],
    }));
    vi.mocked(saveWatchedWork).mockReturnValue(pendingSave.promise);

    render(
      <AuthProvider client={auth.client}>
        <UserLibraryProvider client={{} as SupabaseClient}>
          <LibraryProbe />
        </UserLibraryProvider>
      </AuthProvider>,
    );

    const saveButton = await screen.findByRole("button", {
      name: "A 작품 저장",
    });
    await waitFor(() =>
      expect(saveButton.hasAttribute("disabled")).toBe(false),
    );
    fireEvent.click(saveButton);

    await act(async () => {
      auth.emit(sessionFor("user-b"));
    });
    await waitFor(() =>
      expect(screen.getByTestId("watched-slugs").textContent).toBe("b-work"),
    );

    await act(async () => {
      pendingSave.resolve();
      await pendingSave.promise;
    });

    expect(screen.getByTestId("watched-slugs").textContent).toBe("b-work");
  });
});
