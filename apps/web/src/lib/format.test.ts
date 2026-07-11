import { describe, expect, it } from "vitest";

import {
  confidenceLabel,
  formatPerformanceDate,
  programPublicationMessage,
  statusLabel,
} from "./format";

describe("format helpers", () => {
  it("formats a Korean concert date without timezone drift", () => {
    expect(formatPerformanceDate({ date: "2026-07-31", time: "19:30" })).toBe(
      "7월 31일 (금) 19:30",
    );
  });

  it("maps booking status and confidence to compact labels", () => {
    expect(statusLabel("open")).toBe("예매중");
    expect(statusLabel("upcoming")).toBe("오픈예정");
    expect(confidenceLabel(0.824)).toBe("82%");
  });

  it("explains each deterministic program publication state", () => {
    expect(programPublicationMessage("confirmed")).toBe(
      "NOL 예매 정보에서 확인한 프로그램입니다.",
    );
    expect(programPublicationMessage("image_only")).toBe(
      "상세 정보가 이미지로만 제공되어 곡명을 아직 구조화하지 못했습니다.",
    );
    expect(programPublicationMessage("not_published")).toBe(
      "예매처에 프로그램 정보가 아직 공개되지 않았습니다.",
    );
    expect(programPublicationMessage("selected_on_day")).toBe(
      "프로그램은 공연 당일 공개될 예정입니다.",
    );
    expect(programPublicationMessage("announced_later")).toBe(
      "프로그램은 추후 공개될 예정입니다.",
    );
    expect(programPublicationMessage("unknown")).toBe(
      "프로그램 정보를 확인 중입니다.",
    );
  });
});
