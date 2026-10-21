import { works } from "@classic-hubble/shared";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { YouTubeSearch } from "./YouTubeSearch";
import { identifyYouTubeWorks } from "@/lib/youtube-matching";

const input = () => screen.getByLabelText("유튜브 영상 링크");
const submit = () =>
  fireEvent.click(screen.getByRole("button", { name: "작품 찾기" }));
const video = {
  id: "AbCdEf123_-",
  title: "Beethoven Symphony No. 5 Op. 67",
  description: "",
  channelTitle: "Concert",
};
const matchedResponse = (value = video) =>
  Response.json({ video: value, result: identifyYouTubeWorks(value, works) });
afterEach(() => vi.unstubAllGlobals());

describe("YouTube search", () => {
  it("validates the URL without requesting anything", () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    render(<YouTubeSearch />);
    fireEvent.change(input(), { target: { value: "invalid" } });
    submit();
    expect(screen.getByRole("alert").textContent).toContain("유튜브 영상 링크");
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("shows candidates, source evidence and a work-detail link", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(matchedResponse()));
    render(<YouTubeSearch />);
    fireEvent.change(input(), {
      target: { value: `https://youtu.be/${video.id}` },
    });
    submit();
    const link = await screen.findByRole("link", {
      name: /루트비히 판 베토벤 · 교향곡 5번/,
    });
    expect(link.getAttribute("href")).toBe("/works/beethoven-symphony-5");
    expect(
      screen
        .getByRole("link", { name: "YouTube에서 보기" })
        .getAttribute("href"),
    ).toBe(`https://www.youtube.com/watch?v=${video.id}`);
    expect(screen.getByText("작곡가·작품번호 일치")).toBeTruthy();
  });
  it("distinguishes unavailable video from missing work metadata", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        Response.json({ error: "video_unavailable" }, { status: 404 }),
      )
      .mockResolvedValueOnce(
        matchedResponse({ ...video, title: "Piano", description: "" }),
      );
    vi.stubGlobal("fetch", fetcher);
    render(<YouTubeSearch />);
    fireEvent.change(input(), {
      target: { value: `https://youtu.be/${video.id}` },
    });
    submit();
    expect((await screen.findByRole("alert")).textContent).toContain("비공개");
    submit();
    expect(await screen.findByText("작품을 찾지 못했습니다.")).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });
  it("renders multiple described pieces as separate choices", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          matchedResponse({
            ...video,
            title: "Concert",
            description: "0:00 Beethoven Op. 67\n30:00 Rachmaninoff Op. 18",
          }),
        ),
    );
    render(<YouTubeSearch />);
    fireEvent.change(input(), {
      target: { value: `https://youtu.be/${video.id}` },
    });
    submit();
    expect(
      await screen.findByRole("link", {
        name: /루트비히 판 베토벤 · 교향곡 5번/,
      }),
    ).toBeTruthy();
    expect(
      screen.getByRole("link", {
        name: /세르게이 라흐마니노프 · 피아노 협주곡 2번/,
      }),
    ).toBeTruthy();
  });
  it("clears a pending result when the input changes", async () => {
    let resolve!: (response: Response) => void;
    const fetcher = vi.fn().mockImplementation(
      () =>
        new Promise<Response>((done) => {
          resolve = done;
        }),
    );
    vi.stubGlobal("fetch", fetcher);
    render(<YouTubeSearch />);
    fireEvent.change(input(), {
      target: { value: `https://youtu.be/${video.id}` },
    });
    submit();
    expect(
      (screen.getByRole("button", { name: "찾는 중" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    fireEvent.change(input(), {
      target: { value: "https://youtu.be/Different01" },
    });
    await act(async () => {
      resolve(Response.json({ video }));
    });
    await waitFor(() => expect(screen.queryByText(video.title)).toBeNull());
  });
});
