"""Parses GitHub's unified-diff `patch` text (from `GET
.../pulls/{number}/files`) into the set of line numbers actually added, in
the *new* file's line numbering — enough to answer "which of this file's
indexed symbols does this diff touch" (app/pr_analysis/context.py) without
a full diff/patch library. Only hunk headers and +/- line prefixes are
understood; this is not a general-purpose diff parser."""

import re

_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_patch_added_lines(patch: str | None) -> set[int]:
    if not patch:
        return set()

    added: set[int] = set()
    new_line = 0
    for line in patch.splitlines():
        header_match = _HUNK_HEADER.match(line)
        if header_match:
            new_line = int(header_match.group(1))
            continue
        if line.startswith("\\"):
            continue  # "\ No newline at end of file" — not a real line
        if line.startswith("+"):
            added.add(new_line)
            new_line += 1
        elif line.startswith("-"):
            continue  # removed line — doesn't exist in the new file
        else:
            new_line += 1  # unchanged context line
    return added
