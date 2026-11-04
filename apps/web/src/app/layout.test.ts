import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/font/google", () => ({
  Geist: () => ({ variable: "font-sans" }),
  Geist_Mono: () => ({ variable: "font-mono" }),
}));

import { metadata } from "./layout";

describe("Hubble brand icons", () => {
  it("uses the text-free telescope for browser and Apple icons", () => {
    expect(metadata.icons).toEqual({
      icon: [{ url: "/brand/hubble-icon-32.png", sizes: "32x32", type: "image/png" }],
      apple: [{ url: "/brand/hubble-apple-icon.png", sizes: "180x180", type: "image/png" }],
    });
  });

  it("provides correctly sized telescope icons for installed apps", () => {
    const manifest = JSON.parse(readFileSync(resolve(process.cwd(), "public/manifest.webmanifest"), "utf8"));
    expect(manifest.icons).toEqual([
      { src: "/brand/hubble-icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/brand/hubble-icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
    ]);
  });
});
