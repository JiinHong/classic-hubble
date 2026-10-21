import Link from "next/link";

export default function YouTubePrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl space-y-6 px-4 py-10 text-sm leading-7 text-stone-700">
      <h1 className="text-2xl font-bold text-stone-950">
        유튜브 검색 데이터 처리 안내
      </h1>
      <p>
        적용일: 2026년 10월 21일. 이 안내는 Classic Hubble의 유튜브 링크 검색
        기능에 적용됩니다.
      </p>
      <section>
        <h2 className="font-bold text-stone-950">조회하는 정보와 목적</h2>
        <p>
          입력한 링크에서 영상 ID를 추출해 YouTube Data API로 영상 제목, 설명,
          채널 표시명을 조회합니다. 이 정보를 작품 DB와 비교해 검색 후보를
          제공합니다. 유튜브 계정 로그인, 시청 기록, 영상 파일, 음성은 수집하지
          않습니다.
        </p>
      </section>
      <section>
        <h2 className="font-bold text-stone-950">저장과 삭제</h2>
        <p>
          이 기능은 영상 링크와 조회 결과를 데이터베이스에 저장하지 않습니다.
          서버 메모리의 조회 결과는 60초 동안 재사용하며, 요청 IP는 1분 단위의
          과도한 요청 제한에 사용합니다. 유효기간이 지난 메모리 항목은 다음 조회
          요청에서 정리되거나 서버 프로세스 종료 시 사라집니다. 화면의 조회
          결과는 입력을 바꾸거나 페이지를 닫으면 제거됩니다. 호스팅 및 네트워크
          제공자의 운영·보안 로그 처리는 별도로 적용될 수 있습니다.
        </p>
      </section>
      <section>
        <h2 className="font-bold text-stone-950">외부 서비스</h2>
        <p>
          영상 ID는 Google의 YouTube API에 전송됩니다. 결과 화면의 썸네일은
          YouTube 이미지 서버에서 불러오므로 브라우저의 네트워크 정보가 Google에
          전달될 수 있습니다. 이 검색 기능에서 영상 정보를 광고나 외부 LLM에
          전송하지 않습니다.
        </p>
        <p>
          <a
            className="underline"
            href="https://policies.google.com/privacy"
            target="_blank"
            rel="noreferrer"
          >
            Google 개인정보처리방침
          </a>{" "}
          ·{" "}
          <a
            className="underline"
            href="https://www.youtube.com/t/terms"
            target="_blank"
            rel="noreferrer"
          >
            YouTube 이용약관
          </a>
        </p>
      </section>
      <Link href="/youtube" className="inline-block font-bold text-emerald-800">
        유튜브 검색으로 돌아가기
      </Link>
    </main>
  );
}
