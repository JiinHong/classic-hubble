import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { describe, expect, it } from "vitest";

import {
  loadUserLibrary,
  saveWatchedWork,
} from "./user-library";

type CapturedRequest = {
  body: unknown;
  method: string;
  url: URL;
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
    status,
  });
}

function emptyResponse(status = 201) {
  return new Response(null, { status });
}

function createTestClient(
  handler: (request: Request) => Promise<Response> | Response,
): SupabaseClient {
  const customFetch: typeof fetch = async (input, init) => {
    return handler(new Request(input, init));
  };

  return createClient("https://example.supabase.co", "sb_publishable_test", {
    auth: {
      autoRefreshToken: false,
      detectSessionInUrl: false,
      persistSession: false,
      storage: {
        async getItem() {
          return null;
        },
        async removeItem() {},
        async setItem() {},
      },
    },
    global: { fetch: customFetch },
  });
}

async function captureRequest(request: Request): Promise<CapturedRequest> {
  const text = await request.clone().text();
  return {
    body: text ? JSON.parse(text) : null,
    method: request.method,
    url: new URL(request.url),
  };
}

describe("Supabase user library", () => {
  it("loads only the current user's watched works without reading or changing alert settings", async () => {
    const requests: CapturedRequest[] = [];
    const client = createTestClient(async (request) => {
      requests.push(await captureRequest(request));
      const path = new URL(request.url).pathname;

      if (path.endsWith("/watchlist_items")) {
        return jsonResponse([
          { works: { slug: "beethoven-symphony-5" } },
          { works: [{ slug: "dvorak-symphony-9" }] },
        ]);
      }
      return jsonResponse([{ channel: "email", enabled: false }]);
    });

    const result = await loadUserLibrary(client, "user-1");

    expect(result).toEqual({
      watchedSlugs: ["beethoven-symphony-5", "dvorak-symphony-9"],
    });
    expect(requests.map((request) => request.url.pathname).sort()).toEqual([
      "/rest/v1/watchlist_items",
    ]);
    const watchlistRequest = requests.find((request) =>
      request.url.pathname.endsWith("/watchlist_items"),
    );
    expect(watchlistRequest?.url.searchParams.get("select")).toBe("works(slug)");
    expect(watchlistRequest?.url.searchParams.get("user_id")).toBe("eq.user-1");
  });

  it("prepares the profile and upserts a watched work", async () => {
    const requests: CapturedRequest[] = [];
    const client = createTestClient(async (request) => {
      const captured = await captureRequest(request);
      requests.push(captured);

      if (captured.url.pathname.endsWith("/works")) {
        return jsonResponse([{ id: "work-1" }]);
      }
      return emptyResponse();
    });

    await saveWatchedWork(
      client,
      { id: "user-1", email: "member@example.com" },
      "beethoven-symphony-5",
      true,
    );

    expect(requests.map((request) => [request.method, request.url.pathname])).toEqual([
      ["POST", "/rest/v1/profiles"],
      ["GET", "/rest/v1/works"],
      ["POST", "/rest/v1/watchlist_items"],
    ]);
    expect(requests[0]?.body).toEqual({ id: "user-1", email: "member@example.com" });
    expect(requests[2]?.body).toEqual({ user_id: "user-1", work_id: "work-1" });
  });

  it("deletes a watched work for the current owner", async () => {
    const requests: CapturedRequest[] = [];
    const client = createTestClient(async (request) => {
      const captured = await captureRequest(request);
      requests.push(captured);
      return captured.url.pathname.endsWith("/works")
        ? jsonResponse([{ id: "work-1" }])
        : emptyResponse(204);
    });

    await saveWatchedWork(
      client,
      { id: "user-1", email: "member@example.com" },
      "beethoven-symphony-5",
      false,
    );

    const deletion = requests.at(-1);
    expect(deletion?.method).toBe("DELETE");
    expect(deletion?.url.pathname).toBe("/rest/v1/watchlist_items");
    expect(deletion?.url.searchParams.get("user_id")).toBe("eq.user-1");
    expect(deletion?.url.searchParams.get("work_id")).toBe("eq.work-1");
  });

});
