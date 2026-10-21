import { parseYouTubeUrl, type YouTubeVideo } from "./youtube";

type Options = {
  apiKey: () => string | undefined;
  fetcher?: typeof fetch;
  now?: () => number;
};

const reply = (body: object, status = 200) =>
  Response.json(body, { status, headers: { "Cache-Control": "no-store" } });

async function readBody(request: Request): Promise<string | null> {
  if (Number(request.headers.get("content-length")) > 4096) return null;
  const reader = request.body?.getReader();
  if (!reader) return "";
  const chunks: Uint8Array[] = [];
  let length = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    length += value.length;
    if (length > 4096) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.length;
  }
  return new TextDecoder().decode(bytes);
}

export function createYouTubeHandler({
  apiKey,
  fetcher = fetch,
  now = Date.now,
}: Options) {
  const cache = new Map<string, { expires: number; video: YouTubeVideo }>();
  const clients = new Map<string, { expires: number; requests: number }>();
  return async (request: Request) => {
    const origin = request.headers.get("origin");
    if (request.headers.get("sec-fetch-site") === "cross-site")
      return reply({ error: "invalid_origin" }, 403);
    if (origin) {
      try {
        const source = new URL(origin);
        const host = request.headers.get("host") ?? new URL(request.url).host;
        if (
          !["http:", "https:"].includes(source.protocol) ||
          source.host !== host
        )
          return reply({ error: "invalid_origin" }, 403);
      } catch {
        return reply({ error: "invalid_origin" }, 403);
      }
    }
    if (
      request.headers.get("content-type")?.split(";")[0].trim() !==
      "application/json"
    )
      return reply({ error: "invalid_request" }, 415);
    let id: string | null;
    try {
      const raw = await readBody(request);
      if (raw === null) return reply({ error: "invalid_request" }, 413);
      const body: unknown = JSON.parse(raw);
      id =
        body &&
        typeof body === "object" &&
        "url" in body &&
        typeof body.url === "string"
          ? parseYouTubeUrl(body.url)
          : null;
    } catch {
      return reply({ error: "invalid_request" }, 400);
    }
    if (!id) return reply({ error: "invalid_url" }, 400);
    const key = apiKey()?.trim();
    if (!key) return reply({ error: "not_configured" }, 503);
    const time = now();
    for (const [client, value] of clients)
      if (value.expires <= time) clients.delete(client);
    // Best-effort per-instance throttle, not a distributed quota guarantee.
    const client = (
      request.headers.get("x-forwarded-for")?.split(",")[0].trim() || "unknown"
    ).slice(0, 64);
    const usage = clients.get(client) ?? {
      expires: time + 60_000,
      requests: 0,
    };
    if (
      usage.requests >= 10 ||
      (!clients.has(client) && clients.size >= 10_000)
    )
      return reply({ error: "rate_limited" }, 429);
    usage.requests++;
    clients.set(client, usage);
    for (const [videoId, value] of cache)
      if (value.expires <= time) cache.delete(videoId);
    const cached = cache.get(id);
    if (cached) return reply({ video: cached.video });
    try {
      const url = new URL("https://www.googleapis.com/youtube/v3/videos");
      url.search = new URLSearchParams({
        part: "snippet",
        id,
        key,
        fields: "items(id,snippet(title,description,channelTitle))",
      }).toString();
      const response = await fetcher(url, {
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(8000),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => null);
        const quota = error?.error?.errors?.some((entry: { reason?: string }) =>
          ["quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"].includes(
            entry.reason ?? "",
          ),
        );
        return reply(
          { error: quota ? "quota_exceeded" : "upstream_error" },
          quota ? 503 : 502,
        );
      }
      const body = await response.json();
      if (!Array.isArray(body?.items))
        return reply({ error: "upstream_error" }, 502);
      if (!body.items.length) return reply({ error: "video_unavailable" }, 404);
      const item = body.items[0];
      if (
        item?.id !== id ||
        typeof item.snippet?.title !== "string" ||
        typeof item.snippet?.description !== "string" ||
        typeof item.snippet?.channelTitle !== "string" ||
        item.snippet.title.length > 500 ||
        item.snippet.description.length > 20_000 ||
        item.snippet.channelTitle.length > 500
      )
        return reply({ error: "upstream_error" }, 502);
      const video: YouTubeVideo = {
        id,
        title: item.snippet.title,
        description: item.snippet.description,
        channelTitle: item.snippet.channelTitle,
      };
      if (cache.size >= 256) cache.delete(cache.keys().next().value!);
      cache.set(id, { expires: now() + 60_000, video });
      return reply({ video });
    } catch (error) {
      const timeout =
        error &&
        typeof error === "object" &&
        "name" in error &&
        ["TimeoutError", "AbortError"].includes(String(error.name));
      return reply(
        { error: timeout ? "timeout" : "upstream_error" },
        timeout ? 504 : 502,
      );
    }
  };
}
