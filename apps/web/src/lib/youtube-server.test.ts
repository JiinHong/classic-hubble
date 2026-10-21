import { describe, expect, it, vi } from "vitest";
import { createYouTubeHandler } from "./youtube-server";

const id = "AbCdEf123_-";
const request = (body: unknown = {url: `https://youtu.be/${id}`}, origin = "https://classic-hubble.vercel.app") => new Request("https://classic-hubble.vercel.app/api/youtube", {method: "POST", headers: {"content-type": "application/json", origin}, body: JSON.stringify(body)});
const videoResponse = () => Response.json({items: [{id, snippet: {title: "Schumann: Einsame Blumen", description: "Composer: Robert Schumann", channelTitle: "Piano"}}]});

describe("YouTube metadata endpoint", () => {
  it("fetches only the fixed official endpoint and does not return a key", async () => {
    const fetcher = vi.fn().mockResolvedValue(videoResponse());
    const handle = createYouTubeHandler({apiKey: () => "test-secret", fetcher});
    const response = await handle(request());
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.video.id).toBe(id);
    expect(JSON.stringify(body)).not.toContain("test-secret");
    const [url, options] = fetcher.mock.calls[0];
    expect(new URL(url).origin).toBe("https://www.googleapis.com");
    expect(new URL(url).pathname).toBe("/youtube/v3/videos");
    expect(new URL(url).searchParams.get("id")).toBe(id);
    expect(new URL(url).searchParams.get("part")).toBe("snippet");
    expect(options.redirect).toBe("error");
    expect(response.headers.get("cache-control")).toBe("no-store");
  });
  it("rejects arbitrary URLs before any provider request", async () => {
    const fetcher = vi.fn();
    const handle = createYouTubeHandler({apiKey: () => "key", fetcher});
    expect((await handle(request({url: "http://localhost/admin"}))).status).toBe(400);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("rejects cross-origin and oversized requests", async () => {
    const fetcher = vi.fn();
    const handle = createYouTubeHandler({apiKey: () => "key", fetcher});
    expect((await handle(request({}, "https://other.example"))).status).toBe(403);
    expect((await handle(request({url: "x".repeat(5000)}))).status).toBe(413);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("accepts the browser's host when Next.js uses an internal request URL", async () => {
    const handle = createYouTubeHandler({apiKey: () => "key", fetcher: vi.fn().mockImplementation(videoResponse)});
    const forwarded = (origin: string) => new Request("http://localhost:3012/api/youtube", {
      method: "POST", headers: {"content-type": "application/json", host: "127.0.0.1:3012", origin},
      body: JSON.stringify({url: `https://youtu.be/${id}`}),
    });
    expect((await handle(forwarded("http://127.0.0.1:3012"))).status).toBe(200);
    expect((await handle(forwarded("https://other.example"))).status).toBe(403);
    expect((await handle(forwarded("null"))).status).toBe(403);
  });
  it("rejects malformed bodies and wrong content types", async () => {
    const handle = createYouTubeHandler({apiKey: () => "key"});
    expect((await handle(request({url: 123}))).status).toBe(400);
    expect((await handle(new Request("https://classic-hubble.vercel.app/api/youtube", {method:"POST", body:"not json"}))).status).toBe(415);
  });
  it("reports missing configuration without fake results", async () => {
    const handle = createYouTubeHandler({apiKey: () => undefined});
    const response = await handle(request());
    expect(response.status).toBe(503);
    expect((await response.json()).error).toBe("not_configured");
  });
  it("reports missing/deleted/private video as unavailable without guessing why", async () => {
    const handle = createYouTubeHandler({apiKey: () => "key", fetcher: vi.fn().mockResolvedValue(Response.json({items:[]}))});
    expect((await (await handle(request())).json()).error).toBe("video_unavailable");
  });
  it.each([[403,"quotaExceeded","quota_exceeded"], [403,"keyInvalid","upstream_error"], [500,"backendError","upstream_error"]])("sanitizes provider error %s/%s", async (status, reason, expected) => {
    const handle = createYouTubeHandler({apiKey: () => "key", fetcher: vi.fn().mockResolvedValue(Response.json({error:{message:"secret echoed",errors:[{reason}]}},{status: status as number}))});
    const body = await (await handle(request())).json();
    expect(body.error).toBe(expected);
    expect(JSON.stringify(body)).not.toContain("secret");
  });
  it("reports timeouts", async () => {
    const handle = createYouTubeHandler({apiKey: () => "key", fetcher: vi.fn().mockRejectedValue(new DOMException("timeout", "TimeoutError"))});
    expect((await (await handle(request())).json()).error).toBe("timeout");
  });
  it("rejects malformed or mismatched provider metadata", async () => {
    const handle = createYouTubeHandler({apiKey: () => "key", fetcher: vi.fn().mockResolvedValue(Response.json({items:[{id:"other", snippet:{title:123}}]}))});
    expect((await (await handle(request())).json()).error).toBe("upstream_error");
  });
  it("reuses metadata for 60 seconds, then refreshes", async () => {
    let time = 1000;
    const fetcher = vi.fn().mockImplementation(videoResponse);
    const handle = createYouTubeHandler({apiKey: () => "key", fetcher, now: () => time});
    await handle(request()); await handle(request());
    expect(fetcher).toHaveBeenCalledTimes(1);
    time += 61000;
    await handle(request());
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
  it("throttles requests within one instance", async () => {
    const handle = createYouTubeHandler({apiKey: () => "key", fetcher: vi.fn().mockImplementation(videoResponse)});
    for (let i=0; i<10; i++) expect((await handle(request())).status).toBe(200);
    expect((await handle(request())).status).toBe(429);
  });
});
