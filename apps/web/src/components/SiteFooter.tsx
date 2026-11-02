export function SiteFooter() {
  return (
    <footer className="bg-white text-neutral-400">
      <div className="mx-auto max-w-4xl px-4 py-6 text-center sm:px-8">
        <p className="text-xs">
          Classic Hubble by Jimin &amp; Jinhong
        </p>
        <p className="mt-1 text-xs">
          © 2026 Classic Hubble. All rights reserved.
        </p>
        <details className="mt-3 text-xs text-neutral-500">
        <summary className="mx-auto w-fit py-1">출처 · 라이선스</summary>
        <p className="mt-3 text-xs leading-5 text-neutral-500">
          출처: (재)예술경영지원센터{" "}
          <a
            href="https://www.kopis.or.kr"
            target="_blank"
            rel="noreferrer"
            className="underline underline-offset-2"
          >
            공연예술통합전산망(www.kopis.or.kr)
          </a>
        </p>
        <p className="mt-1 text-xs leading-5 text-neutral-500">
          작품 자료: Wikidata (CC0), 한국어·영어 위키백과 기여자 (
          <a
            href="https://creativecommons.org/licenses/by-sa/4.0/"
            target="_blank"
            rel="noreferrer"
            className="underline underline-offset-2"
          >
            CC BY-SA 4.0
          </a>
          ).{" "}
          <a
            href="/reference/korean-work-names.json"
            target="_blank"
            rel="noreferrer"
            className="underline underline-offset-2"
          >
            작품명·별칭 출처
          </a>
        </p>
        </details>
      </div>
    </footer>
  );
}
