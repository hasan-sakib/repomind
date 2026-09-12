import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { FieldError } from "./field-error";

describe("FieldError", () => {
  it("renders nothing when there is no message", () => {
    const { container } = render(<FieldError />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the message with an alert role for assistive tech", () => {
    render(<FieldError message="Enter a valid email address" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid email address");
  });
});
