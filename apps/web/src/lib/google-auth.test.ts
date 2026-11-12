import { describe, expect, it, vi } from "vitest";
import { callbackDestination, saveReturnPath, safeReturnPath, takeReturnPath } from "./google-auth";

const origin = "https://classichubble.com";

describe("Google OAuth return path", () => {
  it.each(["https://other.example", "//other.example", "/x/..//other.example", "/auth/callback/?a=1", "/x/../auth/callback", "/\\other.example"])("rejects %s", path => {
    expect(safeReturnPath(path, origin)).toBe("/");
  });

  it("keeps search filters but never carries callback credentials or fragments", () => {
    expect(safeReturnPath("/?q=Beethoven&city=Seoul&period=past&code=test#access_token=test", origin)).toBe("/?q=Beethoven&city=Seoul&period=past");
  });

  it("takes a tab's destination once; unavailable storage defaults to home", () => {
    saveReturnPath("/works/work-a", origin, sessionStorage);
    expect(takeReturnPath(origin, sessionStorage)).toBe("/works/work-a");
    expect(takeReturnPath(origin, sessionStorage)).toBe("/");
    expect(takeReturnPath(origin, null)).toBe("/");
  });
});

describe("Google OAuth callback", () => {
  const callback = (params: string) => new URL(origin + "/auth/callback" + params);
  it("exchanges the code then returns to the user's original search", async () => {
    const exchange = vi.fn().mockResolvedValue({ data: { session: {} }, error: null });
    expect(await callbackDestination(callback("?code=sample"), "/?q=Bach", exchange)).toBe("/?q=Bach");
    expect(exchange).toHaveBeenCalledExactlyOnceWith("sample");
  });

  it.each(["", "?error=access_denied&code=sample", "#error=access_denied"])("never exchanges denied or missing credentials", async params => {
    const exchange = vi.fn();
    const result = await callbackDestination(callback(params), "/watchlist", exchange);
    expect(result).toMatch(/^\/watchlist\?auth_notice=(cancelled|failed)$/);
    expect(exchange).not.toHaveBeenCalled();
  });

  it("returns a retry notice on expired code, absent session or network error", async () => {
    for (const exchange of [vi.fn().mockResolvedValue({ error: {}, data: {} }), vi.fn().mockResolvedValue({ error: null, data: { session: null } }), vi.fn().mockRejectedValue(new Error("internal"))]) {
      expect(await callbackDestination(callback("?code=expired"), "/?q=Bach", exchange)).toBe("/?q=Bach&auth_notice=failed");
    }
  });
});
