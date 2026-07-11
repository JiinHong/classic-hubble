import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PasswordAuthApi } from "@/lib/auth";

import { AuthDialog } from "./AuthDialog";

function createAuth(session: unknown | null): PasswordAuthApi {
  return {
    async signInWithPassword() {
      return { data: { session }, error: null };
    },
    async signUp() {
      return { data: { session }, error: null };
    },
  };
}

describe("AuthDialog", () => {
  it("submits a valid login and reports authentication", async () => {
    const onAuthenticated = vi.fn();
    render(
      <AuthDialog
        auth={createAuth({ access_token: "token" })}
        initialMode="signin"
        onAuthenticated={onAuthenticated}
        onClose={() => undefined}
        open
        redirectUrl="https://classichubble.example/"
      />,
    );

    fireEvent.change(screen.getByLabelText("이메일"), {
      target: { value: "member@example.com" },
    });
    fireEvent.change(screen.getByLabelText("비밀번호"), {
      target: { value: "long-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "로그인" }));

    await waitFor(() => expect(onAuthenticated).toHaveBeenCalledOnce());
  });

  it("keeps the dialog open with an email confirmation result after signup", async () => {
    render(
      <AuthDialog
        auth={createAuth(null)}
        initialMode="signup"
        onAuthenticated={() => undefined}
        onClose={() => undefined}
        open
        redirectUrl="https://classichubble.example/"
      />,
    );

    fireEvent.change(screen.getByLabelText("이메일"), {
      target: { value: "member@example.com" },
    });
    fireEvent.change(screen.getByLabelText("비밀번호"), {
      target: { value: "long-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "회원가입" }));

    expect(
      await screen.findByText("확인 메일을 보냈습니다. 이메일 인증을 완료해 주세요."),
    ).toBeTruthy();
  });
});
