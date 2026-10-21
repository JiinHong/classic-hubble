import { describe, expect, it } from "vitest";
import { parseYouTubeUrl } from "./youtube";

describe("YouTube video URL", () => {
  it.each([
    "https://www.youtube.com/watch?v=AbCdEf123_-&t=30s",
    "https://youtu.be/AbCdEf123_-?si=private-tracking",
    "https://m.youtube.com/shorts/AbCdEf123_-",
    "https://music.youtube.com/watch?v=AbCdEf123_-",
    "https://youtube.com/live/AbCdEf123_-",
    "https://www.youtube-nocookie.com/embed/AbCdEf123_-",
    "www.youtube.com/watch?v=AbCdEf123_-",
  ])("extracts only the video ID from %s", (input) => {
    expect(parseYouTubeUrl(input)).toBe("AbCdEf123_-");
  });

  it.each([
    "https://youtube.com.evil.com/watch?v=AbCdEf123_-",
    "https://evil.com/?url=https://youtube.com/watch?v=AbCdEf123_-",
    "https://youtube.com@evil.com/watch?v=AbCdEf123_-",
    "https://user@youtube.com/watch?v=AbCdEf123_-",
    "http://127.0.0.1/AbCdEf123_-",
    "javascript:alert(1)",
    "https://youtube.com/playlist?list=abc",
    "https://youtube.com/watch?v=short",
    "https://youtube.com/watch?v=AbCdEf123_-&v=Different01",
    "https://youtube.com:444/watch?v=AbCdEf123_-",
    "https://youtu.be/AbCdEf123_-/extra",
    "AbCdEf123_-",
    "",
    "x".repeat(2049),
  ])("rejects unsupported or ambiguous URL %s", (input) => {
    expect(parseYouTubeUrl(input)).toBeNull();
  });
});
