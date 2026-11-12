import type { Metadata } from "next";
import { GoogleAuthCallback } from "@/components/GoogleAuthCallback";

export const metadata: Metadata = {
  title: "Google 로그인 | 클래식허블",
  referrer: "no-referrer",
  robots: { index: false, follow: false },
};

export default function Page() {
  return <GoogleAuthCallback />;
}
