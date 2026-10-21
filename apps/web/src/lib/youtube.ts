export type YouTubeVideo = {
  id: string;
  title: string;
  description: string;
  channelTitle: string;
};
export function parseYouTubeUrl(input: string): string | null {
  if (typeof input !== "string" || input.length > 2048) return null;
  try {
    const value = input.trim();
    const url = new URL(
      /^https?:\/\//i.test(value) ? value : `https://${value}`,
    );
    if (
      !["https:", "http:"].includes(url.protocol) ||
      url.username ||
      url.password ||
      url.port
    )
      return null;
    const hosts = new Set([
      "youtube.com",
      "www.youtube.com",
      "m.youtube.com",
      "music.youtube.com",
    ]);
    let id: string | null = null;
    if (url.hostname === "youtu.be") {
      id = url.pathname.match(/^\/([\w-]{11})\/?$/)?.[1] ?? null;
    } else if (hosts.has(url.hostname) && url.pathname === "/watch") {
      if (url.searchParams.getAll("v").length !== 1) return null;
      id = url.searchParams.get("v");
    } else if (
      hosts.has(url.hostname) ||
      url.hostname === "www.youtube-nocookie.com"
    ) {
      id =
        url.pathname.match(/^\/(?:shorts|live|embed)\/([\w-]{11})\/?$/)?.[1] ??
        null;
    }
    return id && /^[\w-]{11}$/.test(id) ? id : null;
  } catch {
    return null;
  }
}
