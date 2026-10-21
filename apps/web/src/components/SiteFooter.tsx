export function SiteFooter() {
  return (
    <footer className="border-t border-stone-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <p className="text-sm font-black text-stone-800">
          Classic Hubble by Jimin &amp; Jinhong
        </p>
        <p className="mt-1 text-xs font-semibold text-stone-500">
          © 2026 Classic Hubble. All rights reserved.
        </p>
        <p className="mt-3 text-xs leading-5 text-stone-500">
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
        <p className="mt-1 text-xs leading-5 text-stone-500">
          작품 자료: Wikidata (CC0), 한국어 위키백과 기여자 (
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
      </div>
    </footer>
  );
}
