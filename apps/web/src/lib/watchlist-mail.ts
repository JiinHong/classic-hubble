type Event = {event_id: string; recipient: string; subject_line: string; body: string};
type MailWorker = {
  claim(): Promise<Event | null>;
  send(event: Event): Promise<string>;
  finish(event: string, provider: string): Promise<void>;
};

export async function dispatchMail(worker: MailWorker, limit: number) {
  let sent = 0;
  for (; sent < limit; sent++) {
    const event = await worker.claim();
    if (!event) break;
    const provider = await worker.send(event);
    await worker.finish(event.event_id, provider);
  }
  return sent;
}

export function productionMailWorker(token: string, onlyEvent: string | null): MailWorker {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const apikey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  const resend = process.env.RESEND_API_KEY;
  if (!url || !apikey || !resend) throw new Error("Missing mail configuration");
  async function rpc(operation: string, event: string | null, provider?: string) {
    const result = await fetch(url + "/rest/v1/rpc/watchlist_mail_worker", {
      method: "POST", cache: "no-store", signal: AbortSignal.timeout(8000),
      headers: { apikey: apikey!, "Content-Type": "application/json" },
      body: JSON.stringify({token, operation, event, provider})
    });
    if (!result.ok) throw new Error("Mail queue HTTP " + result.status);
    const body = await result.text();
    return body ? JSON.parse(body) : null;
  }
  return {
    claim: () => rpc("claim", onlyEvent),
    finish: async (id, provider) => {
      if (await rpc("finish", id, provider) !== true) throw new Error("Mail acknowledgement failed");
    },
    send: async e => {
      const result = await fetch("https://api.resend.com/emails", {
        method: "POST", cache: "no-store", signal: AbortSignal.timeout(8000),
        headers: {"Content-Type":"application/json", Authorization: "Bearer " + resend,
          "Idempotency-Key": "watchlist-concert/" + e.event_id},
        body: JSON.stringify({from:"클래식허블 <alerts@notify.classichubble.com>", to:[e.recipient],
          subject:e.subject_line.replace(/[\r\n]/g," "), text:e.body})
      });
      if (!result.ok) throw new Error("Resend HTTP " + result.status);
      const {id} = await result.json();
      if (typeof id !== "string" || !id) throw new Error("Missing provider reference");
      return id;
    }
  };
}
