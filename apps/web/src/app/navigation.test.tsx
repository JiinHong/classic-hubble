import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import Loading from "./loading";
import ErrorPage from "./error";

it("provides an accessible loading state during server-side navigation", () => {
  render(<Loading />);
  expect(screen.getByRole("status").getAttribute("aria-busy")).toBe("true");
  expect(screen.getByText("불러오는 중입니다.")).toBeTruthy();
});

it("lets visitors retry an unavailable detail without displaying server internals", () => {
  const reset = vi.fn();
  render(
    <ErrorPage error={new Error("private database details")} reset={reset} />,
  );
  expect(screen.getByRole("alert")).toBeTruthy();
  expect(screen.queryByText("private database details")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
  expect(reset).toHaveBeenCalledOnce();
});
