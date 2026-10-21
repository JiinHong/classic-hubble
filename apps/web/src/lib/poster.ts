export function posterImage(src: string) {
  try {
    const url = new URL(src);
    if (
      ["http:", "https:"].includes(url.protocol) &&
      ["www.kopis.or.kr", "kopis.or.kr"].includes(url.hostname) &&
      url.pathname.startsWith("/upload/pfmPoster/") &&
      !url.username &&
      !url.password &&
      !url.port
    ) {
      url.protocol = "https:";
      url.hostname = "kopis.or.kr";
      return { src: url.href, unoptimized: false };
    }
  } catch {
    // Relative placeholders do not need a remote image request.
  }
  return { src, unoptimized: true };
}
