import { describe, expect, it } from "vitest";
import {
  confidenceLabel,
  formatPerformanceDate,
  programPublicationMessage,
  performedScopeLabel,
  statusLabel,
} from "./format";

describe("performance presentation", () => {
  it("distinguishes identified works from their performed extent", () => {
    expect(performedScopeLabel("excerpt")).toBe("발췌");
    expect(performedScopeLabel("arrangement")).toBe("편곡");
    expect(performedScopeLabel("movement")).toBe("악장 연주");
    expect(performedScopeLabel("unknown")).toBe("연주 범위 미확인");
    expect(performedScopeLabel("full_work")).toBe("전곡");
    expect(performedScopeLabel(null)).toBe("");
    expect(performedScopeLabel(undefined)).toBe("");
  });
  it("formats a Korean concert date without timezone drift", () => {
    expect(formatPerformanceDate({ date: "2026-07-31", time: "19:30" })).toBe(
      "7월 31일 (금) 19:30",
    );
  });

  it("maps confidence to compact labels", () => {
    expect(confidenceLabel(0.824)).toBe("82%");
  });

  it("can include the year when displaying historical concerts", () => {
    expect(formatPerformanceDate({ date: "2024-11-24", time: "16:00" }, true)).toBe(
      "2024년 11월 24일 (일) 16:00",
    );
    expect(formatPerformanceDate({ date: "2024-11-24", endDate: "2024-11-25", time: "16:00" }, true)).toBe(
      "2024.11.24 ~ 2024.11.25",
    );
  });

  it("explains each deterministic program publication state", () => {
    expect(programPublicationMessage("partially_confirmed")).toBe(
      "일부 곡목만 안내되어 있어요.",
    );
    expect(programPublicationMessage("confirmed")).toBe(
      "",
    );
    expect(programPublicationMessage("image_only")).toBe(
      "자세한 곡목은 공연 안내에서 확인해 주세요.",
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
  it("shows the full date range instead of an obsolete opening date for a series", () => {
    expect(
      formatPerformanceDate({
        date: "2024-11-09",
        endDate: "2026-12-31",
        time: "19:00",
      }),
    ).toBe("2024.11.09 ~ 2026.12.31");
  });

  it("does not infer ticket availability from KOPIS performance state", () => {
    expect(statusLabel("open")).toBe("공연 중");
    expect(statusLabel("upcoming")).toBe("공연 예정");
  });
});
