import type {
  ConfidenceLevel,
  Performance,
  ProgramPublicationStatus,
} from "@classic-hubble/shared";

export const formatPerformanceDate = (
  performance: Pick<Performance, "date" | "endDate" | "time">,
) => {
  if (performance.endDate && performance.endDate !== performance.date) {
    return `${performance.date.replaceAll("-", ".")} ~ ${performance.endDate.replaceAll("-", ".")}`;
  }
  const [year, month, day] = performance.date.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  const formatted = new Intl.DateTimeFormat("ko-KR", {
    month: "long",
    day: "numeric",
    weekday: "short",
    timeZone: "UTC",
  }).format(date);

  return `${formatted} ${performance.time}`;
};

export const statusLabel = (status: Performance["status"]) =>
  ({
    open: "공연 중",
    upcoming: "공연 예정",
    soldout: "매진",
    closed: "종료·취소",
  })[status];

export const statusTone = (status: Performance["status"]) =>
  ({
    open: "border-emerald-200 bg-emerald-50 text-emerald-700",
    upcoming: "border-amber-200 bg-amber-50 text-amber-700",
    soldout: "border-stone-200 bg-stone-100 text-stone-500",
    closed: "border-stone-200 bg-stone-100 text-stone-500",
  })[status];

export const sourceTone = (type: ConfidenceLevel) =>
  ({
    official: "border-sky-200 bg-sky-50 text-sky-700",
    verified: "border-emerald-200 bg-emerald-50 text-emerald-700",
    ocr: "border-amber-200 bg-amber-50 text-amber-700",
    estimated: "border-rose-200 bg-rose-50 text-rose-700",
    unknown: "border-stone-200 bg-stone-100 text-stone-500",
  })[type];

export const confidenceLabel = (confidence: number) =>
  `${Math.round(confidence * 100)}%`;

export const programPublicationMessage = (status: ProgramPublicationStatus) =>
  ({
    confirmed: "NOL 예매 정보에서 확인한 프로그램입니다.",
    image_only:
      "상세 정보가 이미지로만 제공되어 곡명을 아직 구조화하지 못했습니다.",
    not_published: "예매처에 프로그램 정보가 아직 공개되지 않았습니다.",
    selected_on_day: "프로그램은 공연 당일 공개될 예정입니다.",
    announced_later: "프로그램은 추후 공개될 예정입니다.",
    unknown: "프로그램 정보를 확인 중입니다.",
  })[status];

export const compactArtists = (artists: string[]) =>
  artists.length > 2
    ? `${artists.slice(0, 2).join(", ")} 외`
    : artists.join(", ");
