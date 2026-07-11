import { NextResponse } from "next/server";

type PushSubscriptionBody = {
  endpoint?: string;
  keys?: {
    p256dh?: string;
    auth?: string;
  };
};

export async function POST(request: Request) {
  const body = (await request.json()) as PushSubscriptionBody;

  if (!body.endpoint || !body.keys?.p256dh || !body.keys.auth) {
    return NextResponse.json(
      { ok: false, error: "invalid_push_subscription" },
      { status: 400 },
    );
  }

  return NextResponse.json({
    ok: true,
    status: "ready_for_supabase_persistence",
  });
}
