import type { Repository } from "@/lib/types";

/** A GitHub blob URL for a file in `repository`, optionally pinned to a
 * specific ref (branch or commit sha) and/or deep-linked to a line range.
 * Defaults to the repository's default branch when no ref is given. */
export function buildBlobUrl(
  repository: Repository,
  path: string,
  options: { ref?: string; startLine?: number | null; endLine?: number | null } = {},
): string {
  const ref = options.ref ?? repository.default_branch;
  const base = `${repository.html_url}/blob/${ref}/${path}`;
  if (options.startLine == null) return base;
  if (options.endLine == null || options.endLine === options.startLine) {
    return `${base}#L${options.startLine}`;
  }
  return `${base}#L${options.startLine}-L${options.endLine}`;
}
