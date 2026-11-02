import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SearchBox } from "./SearchBox";
const suggestion = { slug: "exact-work", title: "피아노 협주곡 2번", composer: "라흐마니노프" };
beforeEach(() => vi.useFakeTimers());
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
async function settle() { await act(async () => { await vi.advanceTimersByTimeAsync(120); }); }
function setup() {
  const onSubmit = vi.fn(), onSelect = vi.fn(), onClear = vi.fn();
  const fetcher = vi.fn<typeof fetch>(async () => Response.json({ suggestions: [suggestion] }));
  vi.stubGlobal("fetch", fetcher);
  render(<SearchBox initialValue="" onSubmit={onSubmit} onSelect={onSelect} onClear={onClear} />);
  const input = screen.getByRole("combobox");
  fireEvent.focus(input);
  return { input, onSubmit, onSelect, onClear, fetcher };
}
describe("autocomplete search input", () => {
  it("only fetches lightweight suggestions while typing; Enter submits the draft", async () => {
    const { input, fetcher, onSubmit } = setup();
    fireEvent.change(input, { target: { value: "라흐" } });
    expect(fetcher).not.toHaveBeenCalled();
    await settle();
    expect(fetcher.mock.calls[0][0]).toContain("/api/catalog/suggest?");
    expect(onSubmit).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledWith("라흐");
  });
  it("selects an exact identity with arrow keys, not a reconstructed query", async () => {
    const { input, onSelect, onSubmit } = setup();
    fireEvent.change(input, { target: { value: "라흐" } }); await settle();
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith(suggestion);
    expect(onSubmit).not.toHaveBeenCalled();
  });
  it("keeps the active keyboard suggestion in view", async () => {
    const { input } = setup();
    fireEvent.change(input, { target: { value: "라흐" } }); await settle();
    const scroll = vi.fn();
    screen.getByRole("option").scrollIntoView = scroll;
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(scroll).toHaveBeenCalledWith({ block: "nearest" });
  });
  it("does not fetch or submit during Korean composition", async () => {
    const { input, fetcher, onSubmit } = setup();
    fireEvent.compositionStart(input);
    fireEvent.change(input, { target: { value: "운명" } }); await settle();
    fireEvent.keyDown(input, { key: "Enter", isComposing: true, keyCode: 229 });
    expect(fetcher).not.toHaveBeenCalled(); expect(onSubmit).not.toHaveBeenCalled();
    fireEvent.compositionEnd(input); await settle();
    expect(fetcher).toHaveBeenCalledOnce();
  });
  it("closes on Escape and clears without fetching an empty catalog", async () => {
    const { input, onClear, fetcher } = setup();
    fireEvent.change(input, { target: { value: "운명" } }); await settle();
    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("listbox")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "검색어 지우기" })); await settle();
    expect(onClear).toHaveBeenCalledOnce(); expect(fetcher).toHaveBeenCalledOnce();
  });
  it("reuses recent suggestions and rejects an old response", async () => {
    const { input, fetcher } = setup();
    fireEvent.change(input, { target: { value: "운명" } }); await settle();
    let resolve!: (r: Response) => void;
    fetcher.mockImplementationOnce(() => new Promise(r => { resolve = r; }));
    fireEvent.change(input, { target: { value: "old" } }); await settle();
    fireEvent.change(input, { target: { value: "운명" } }); await settle();
    await act(async () => resolve(Response.json({ suggestions: [{ ...suggestion, title: "OLD" }] })));
    expect(screen.queryByText("OLD")).toBeNull(); expect(fetcher).toHaveBeenCalledTimes(2);
  });
  it("keeps normal submission available after suggestions fail", async () => {
    const { input, fetcher, onSubmit } = setup();
    fetcher.mockResolvedValueOnce(Response.json({}, { status: 503 }));
    fireEvent.change(input, { target: { value: "unknown" } }); await settle();
    expect(screen.getByRole("alert")).toBeTruthy();
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledWith("unknown");
  });
  it("clears a submitted search when its draft becomes whitespace", async () => {
    const { input, onClear, fetcher } = setup();
    fireEvent.change(input, { target: { value: "   " } }); await settle();
    expect(onClear).toHaveBeenCalledOnce(); expect(fetcher).not.toHaveBeenCalled();
  });
});
