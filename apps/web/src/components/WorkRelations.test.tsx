import { render, screen } from "@testing-library/react";
import { works } from "@classic-hubble/shared";
import { describe, expect, it } from "vitest";
import { WorkRelations } from "./WorkRelations";

describe("work relationships", () => {
  it("renders distinct parent and component navigation", () => {
    const ref = { slug: "flower", title: "Einsame Blumen", titleKo: "고독한 꽃", catalogue: "", position: 3 };
    render(<WorkRelations work={{ ...works[0], parts: [ref] }} />);
    expect(screen.getByRole("heading", { name: "구성곡" })).not.toBeNull();
    expect(screen.getByRole("link", { name: /고독한 꽃/ }).getAttribute("href")).toBe("/works/flower");
  });
  it("does not render an empty relationship section", () => {
    const { container } = render(<WorkRelations work={works[0]} />);
    expect(container.innerHTML).toBe("");
  });
});
