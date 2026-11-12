export const callbackPath = "/auth/callback";
const returnKey = "classic-hubble:oauth-return";
const searchKeys = new Set(["q", "composer", "work", "mode", "city", "period"]);

export function safeReturnPath(raw: string | null, origin: string) {
  if (!raw?.startsWith("/") || raw.startsWith("//") || raw.includes("\\")) return "/";
  try {
    const url = new URL(raw, origin);
    const path = decodeURIComponent(url.pathname);
    if (url.origin !== origin || path.startsWith("//") || path.includes("\\") ||
      /^\/(?:auth|api)(?:\/|$)/i.test(path)) return "/";
    for (const key of [...url.searchParams.keys()]) {
      if (!searchKeys.has(key)) url.searchParams.delete(key);
    }
    return url.pathname + url.search;
  } catch { return "/"; }
}

export function tabStorage() {
  try { return window.sessionStorage; } catch { return null; }
}

export function saveReturnPath(path: string, origin: string, storage: Storage | null) {
  try { storage?.setItem(returnKey, safeReturnPath(path, origin)); } catch { /* Optional return hint. */ }
}

export function takeReturnPath(origin: string, storage: Storage | null) {
  try {
    const path = storage?.getItem(returnKey) ?? null;
    storage?.removeItem(returnKey);
    return safeReturnPath(path, origin);
  } catch { return "/"; }
}

type Exchange = (code: string) => Promise<{ data: { session: unknown }; error: unknown }>;

export async function callbackDestination(callback: URL, saved: string, exchange: Exchange | null) {
  const destination = new URL(safeReturnPath(saved, callback.origin), callback.origin);
  const hash = new URLSearchParams(callback.hash.slice(1));
  const error = callback.searchParams.get("error") || hash.get("error") ||
    callback.searchParams.get("error_code") || hash.get("error_code");
  const code = callback.searchParams.get("code");
  if (!error && code && exchange) {
    try {
      const result = await exchange(code);
      if (!result.error && result.data.session) return destination.pathname + destination.search;
    } catch { /* Don't expose provider errors, codes or tokens. */ }
  }
  destination.searchParams.set("auth_notice", error === "access_denied" ? "cancelled" : "failed");
  return destination.pathname + destination.search;
}
