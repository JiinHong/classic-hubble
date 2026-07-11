"use client";

import { CheckCircle2, LoaderCircle, LockKeyhole, Mail, X } from "lucide-react";
import { FormEvent, useState } from "react";

import {
  authenticateWithPassword,
  type AuthMode,
  type PasswordAuthApi,
} from "@/lib/auth";

type AuthDialogProps = {
  auth: PasswordAuthApi;
  initialMode: AuthMode;
  onAuthenticated: () => void;
  onClose: () => void;
  open: boolean;
  redirectUrl: string;
};

export function AuthDialog({
  auth,
  initialMode,
  onAuthenticated,
  onClose,
  open,
  redirectUrl,
}: AuthDialogProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setSubmitting(true);

    try {
      const result = await authenticateWithPassword(
        auth,
        mode,
        { email, password },
        redirectUrl,
      );

      if (result.requiresEmailConfirmation) {
        setMessage("확인 메일을 보냈습니다. 이메일 인증을 완료해 주세요.");
      } else {
        onAuthenticated();
      }
    } catch (submissionError) {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : "인증 요청을 처리하지 못했습니다.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-stone-950/55 px-4 py-8"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target && !submitting) onClose();
      }}
    >
      <section
        aria-labelledby="auth-dialog-title"
        aria-modal="true"
        className="w-full max-w-md rounded-lg border border-stone-200 bg-white p-6 shadow-2xl"
        role="dialog"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-black text-emerald-700">클래식허블 계정</p>
            <h2 id="auth-dialog-title" className="mt-1 text-2xl font-black text-stone-950">
              {mode === "signin" ? "로그인" : "회원가입"}
            </h2>
          </div>
          <button
            aria-label="닫기"
            className="grid size-10 place-items-center rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-950 disabled:opacity-40"
            disabled={submitting}
            onClick={onClose}
            title="닫기"
            type="button"
          >
            <X aria-hidden="true" className="size-5" />
          </button>
        </div>

        <div
          aria-label="인증 방식"
          className="mt-5 grid grid-cols-2 rounded-md bg-stone-100 p-1"
          role="tablist"
        >
          {(["signin", "signup"] as const).map((item) => (
            <button
              aria-selected={mode === item}
              className={`h-9 rounded-md text-sm font-black transition ${
                mode === item
                  ? "bg-white text-stone-950 shadow-sm"
                  : "text-stone-500 hover:text-stone-950"
              }`}
              key={item}
              onClick={() => {
                setMode(item);
                setError(null);
                setMessage(null);
              }}
              role="tab"
              type="button"
            >
              {item === "signin" ? "로그인" : "회원가입"}
            </button>
          ))}
        </div>

        <form className="mt-5 grid gap-4" onSubmit={handleSubmit}>
          <label className="grid gap-2 text-sm font-black text-stone-700">
            이메일
            <span className="relative">
              <Mail
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-stone-400"
              />
              <input
                autoComplete="email"
                className="h-11 w-full rounded-md border border-stone-300 bg-white pl-10 pr-3 text-sm font-semibold text-stone-950 outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                inputMode="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@example.com"
                type="email"
                value={email}
              />
            </span>
          </label>

          <label className="grid gap-2 text-sm font-black text-stone-700">
            비밀번호
            <span className="relative">
              <LockKeyhole
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-stone-400"
              />
              <input
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
                className="h-11 w-full rounded-md border border-stone-300 bg-white pl-10 pr-3 text-sm font-semibold text-stone-950 outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                minLength={8}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                value={password}
              />
            </span>
          </label>

          {error ? (
            <p className="rounded-md bg-rose-50 px-3 py-2 text-sm font-bold text-rose-800" role="alert">
              {error}
            </p>
          ) : null}
          {message ? (
            <p
              className="flex items-start gap-2 rounded-md bg-emerald-50 px-3 py-2 text-sm font-bold text-emerald-800"
              role="status"
            >
              <CheckCircle2 aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              {message}
            </p>
          ) : null}

          <button
            className="mt-1 inline-flex h-11 items-center justify-center gap-2 rounded-md bg-stone-950 px-4 text-sm font-black text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-55"
            disabled={submitting}
            type="submit"
          >
            {submitting ? (
              <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
            ) : null}
            {mode === "signin" ? "로그인" : "회원가입"}
          </button>
        </form>
      </section>
    </div>
  );
}
