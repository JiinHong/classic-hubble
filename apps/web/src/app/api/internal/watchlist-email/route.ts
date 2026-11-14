import { createHash, timingSafeEqual } from "node:crypto";
import { dispatchMail, productionMailWorker } from "@/lib/watchlist-mail";

export const maxDuration = 60;
const hash = (s: string) => createHash("sha256").update(s).digest();

export async function POST(req: Request) {
  const token = process.env.WATCHLIST_MAIL_TOKEN;
  if (!token || !timingSafeEqual(hash(req.headers.get("authorization") ?? ""),hash("Bearer " + token)))
    return new Response(null, {status: 401});
  const event = new URL(req.url).searchParams.get("event");
  if (event !== null && !/^[a-f\d]{8}(?:-[a-f\d]{4}){3}-[a-f\d]{12}$/i.test(event))
    return new Response(null, {status:400});
  try {
    const sent = await dispatchMail(productionMailWorker(token, event), event ? 1 : 10);
    return Response.json({sent}, {headers: {"Cache-Control":"no-store"}});
  } catch (err) {
    // Never log recipients, provider response bodies or request headers.
    console.error("Watchlist dispatch failed:", err instanceof Error ? err.message : "unknown");
    return Response.json({error:"dispatch_failed"}, {status:502});
  }
}
