import { describe, expect, it } from "vitest";

import {
  authenticateWithPassword,
  authErrorMessage,
  validateCredentials,
} from "./auth";

describe("password authentication", () => {
  it("normalizes credentials before signing in", async () => {
    const calls: unknown[] = [];
    const auth = {
      async signInWithPassword(credentials: { email: string; password: string }) {
        calls.push(credentials);
        return {
          data: { session: { access_token: "token" } },
          error: null,
        };
      },
      async signUp() {
        throw new Error("unexpected signup");
      },
    };

    const result = await authenticateWithPassword(
      auth,
      "signin",
      { email: "  USER@example.com ", password: "long-password" },
      "https://classichubble.example",
    );

    expect(calls).toEqual([{ email: "user@example.com", password: "long-password" }]);
    expect(result).toEqual({ requiresEmailConfirmation: false });
  });

  it("marks a signup without a session as awaiting email confirmation", async () => {
    const calls: unknown[] = [];
    const auth = {
      async signInWithPassword() {
        throw new Error("unexpected sign in");
      },
      async signUp(input: unknown) {
        calls.push(input);
        return { data: { session: null }, error: null };
      },
    };

    const result = await authenticateWithPassword(
      auth,
      "signup",
      { email: "member@example.com", password: "long-password" },
      "https://classichubble.example/",
    );

    expect(calls).toEqual([
      {
        email: "member@example.com",
        password: "long-password",
        options: { emailRedirectTo: "https://classichubble.example/" },
      },
    ]);
    expect(result).toEqual({ requiresEmailConfirmation: true });
  });

  it("rejects invalid credentials before an auth request", () => {
    expect(validateCredentials("not-an-email", "short")).toBe(
      "올바른 이메일 주소를 입력해 주세요.",
    );
    expect(validateCredentials("member@example.com", "short")).toBe(
      "비밀번호는 8자 이상이어야 합니다.",
    );
  });

  it("maps common provider errors to concise Korean messages", () => {
    expect(authErrorMessage("Invalid login credentials")).toBe(
      "이메일 또는 비밀번호를 확인해 주세요.",
    );
    expect(authErrorMessage("Email not confirmed")).toBe(
      "이메일 확인을 완료한 뒤 로그인해 주세요.",
    );
    expect(authErrorMessage("User already registered")).toBe(
      "이미 가입된 이메일입니다.",
    );
  });
});
