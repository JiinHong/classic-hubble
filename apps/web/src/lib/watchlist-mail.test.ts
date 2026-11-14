import { describe, expect, it, vi } from "vitest";
import { dispatchMail } from "./watchlist-mail";

const event = {event_id: "one", recipient: "test@example.com",
  body: "알림 본문", subject_line: "공연 알림"};

describe("watchlist mail dispatch", () => {
  it("does not contact the provider for an empty second claim", async () => {
    let done = false;
    const send = vi.fn(async () => "provider-id");
    const finish = vi.fn(async () => { done = true; });
    const db = { claim: async () => done ? null : event, finish, send };
    expect(await dispatchMail(db, 1)).toBe(1);
    expect(await dispatchMail(db, 1)).toBe(0);
    expect(send).toHaveBeenCalledTimes(1);
    expect(finish).toHaveBeenCalledWith("one", "provider-id");
  });
  it("never marks a failed provider request as accepted", async () => {
    const finish = vi.fn();
    await expect(dispatchMail({claim: async () => event, finish,
      send: async () => { throw new Error("provider unavailable"); }}, 1)).rejects.toThrow();
    expect(finish).not.toHaveBeenCalled();
  });
});
