import { describe, expect, it } from "vitest";
import { posterImage } from "./poster";

describe("poster delivery", () => {
  it("avoids the KOPIS HTTP and www redirects and enables resizing", () => {
    expect(
      posterImage("http://www.kopis.or.kr/upload/pfmPoster/example.jpg"),
    ).toEqual({
      src: "https://kopis.or.kr/upload/pfmPoster/example.jpg",
      unoptimized: false,
    });
  });
  it("keeps unknown hosts and non-poster paths outside the image proxy", () => {
    expect(posterImage("https://example.com/poster.jpg").unoptimized).toBe(
      true,
    );
    expect(posterImage("https://kopis.or.kr/other.jpg").unoptimized).toBe(true);
    expect(
      posterImage("https://kopis.or.kr.evil.test/upload/a.jpg").unoptimized,
    ).toBe(true);
  });
  it("keeps local placeholders available", () => {
    expect(posterImage("/window.svg").src).toBe("/window.svg");
  });
});
