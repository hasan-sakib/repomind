import { describe, expect, it } from "vitest";

import { buildBlobUrl } from "./github-url";
import { makeRepository } from "@/test/factories";

// This function backs the "view source reference" flow — clicking a chat
// citation must land on the exact file/line range it claims to.
describe("buildBlobUrl", () => {
  const repository = makeRepository({
    html_url: "https://github.com/acme/widgets",
    default_branch: "main",
  });

  it("defaults to the repository's default branch with no ref given", () => {
    expect(buildBlobUrl(repository, "src/index.ts")).toBe(
      "https://github.com/acme/widgets/blob/main/src/index.ts",
    );
  });

  it("pins to an explicit ref (e.g. a commit sha) when given", () => {
    expect(buildBlobUrl(repository, "src/index.ts", { ref: "abc123" })).toBe(
      "https://github.com/acme/widgets/blob/abc123/src/index.ts",
    );
  });

  it("deep-links to a single line", () => {
    expect(buildBlobUrl(repository, "src/index.ts", { startLine: 42 })).toBe(
      "https://github.com/acme/widgets/blob/main/src/index.ts#L42",
    );
  });

  it("deep-links to a line range", () => {
    expect(buildBlobUrl(repository, "src/index.ts", { startLine: 10, endLine: 20 })).toBe(
      "https://github.com/acme/widgets/blob/main/src/index.ts#L10-L20",
    );
  });

  it("collapses an identical start/end line to a single-line link", () => {
    expect(buildBlobUrl(repository, "src/index.ts", { startLine: 10, endLine: 10 })).toBe(
      "https://github.com/acme/widgets/blob/main/src/index.ts#L10",
    );
  });

  it("ignores endLine when startLine is absent", () => {
    expect(buildBlobUrl(repository, "src/index.ts", { endLine: 20 })).toBe(
      "https://github.com/acme/widgets/blob/main/src/index.ts",
    );
  });
});
