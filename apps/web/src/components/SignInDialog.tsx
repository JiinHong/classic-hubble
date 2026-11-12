"use client";

import Image from "next/image";
import { LoaderCircle, X } from "lucide-react";
import { useLayoutEffect, useRef } from "react";

type SignInDialogProps = {
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onContinue: () => void;
};

export function SignInDialog({ busy, error, onClose, onContinue }: SignInDialogProps) {
  const dialog = useRef<HTMLDialogElement>(null);
  const pressedBackdrop = useRef(false);

  useLayoutEffect(() => {
    const element = dialog.current!;
    const opener = document.activeElement;
    element.showModal();
    return () => {
      element.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus({ preventScroll: true });
    };
  }, []);

  return (
    <dialog
      ref={dialog}
      aria-label="클래식허블 로그인"
      className="sign-in-dialog fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-96 overflow-y-auto rounded-lg border border-neutral-200 bg-white p-0 text-neutral-900 shadow-xl backdrop:bg-neutral-950/40"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      onPointerDown={(event) => { pressedBackdrop.current = event.target === event.currentTarget; }}
      onClick={(event) => {
        if (!busy && pressedBackdrop.current && event.target === event.currentTarget) onClose();
      }}
    >
      <div className="relative flex flex-col items-center px-6 pb-8 pt-10 sm:px-8">
        <Image src="/brand/hubble-logo.png" alt="클래식허블" width={72} height={48} unoptimized className="h-12 w-auto" />
        {error && <p role="alert" className="mt-4 text-center text-sm text-red-700">{error}</p>}
        <button
          type="button"
          disabled={busy}
          onClick={onContinue}
          className="mt-8 inline-flex min-h-12 w-full items-center justify-center gap-2.5 rounded-full border border-[#747775] bg-white px-4 text-sm font-medium text-[#1f1f1f] transition-colors hover:bg-neutral-50 disabled:opacity-65"
        >
          {busy ? <LoaderCircle aria-hidden="true" className="size-5 animate-spin motion-reduce:animate-none" /> :
            <Image src="/brand/google-g.png" alt="" width={20} height={20} className="size-5 object-contain" unoptimized />}
          {busy ? "Google로 이동 중…" : "Google로 계속하기"}
        </button>
        <button type="button" title="닫기" aria-label="닫기" disabled={busy} onClick={onClose}
          className="icon-button absolute right-1.5 top-1.5"><X aria-hidden="true" className="size-4" /></button>
      </div>
    </dialog>
  );
}
