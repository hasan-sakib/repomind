from app.pr_analysis.diff_parser import parse_patch_added_lines


def test_no_patch_returns_empty_set() -> None:
    assert parse_patch_added_lines(None) == set()
    assert parse_patch_added_lines("") == set()


def test_simple_addition() -> None:
    patch = "@@ -1,2 +1,3 @@\n line one\n+line two (new)\n line three"
    assert parse_patch_added_lines(patch) == {2}


def test_pure_insertion_hunk() -> None:
    patch = "@@ -5,0 +6,2 @@ def existing():\n+    new_line_one()\n+    new_line_two()"
    assert parse_patch_added_lines(patch) == {6, 7}


def test_removed_lines_dont_consume_new_line_numbers() -> None:
    patch = "@@ -1,3 +1,2 @@\n context\n-removed line\n+replacement line"
    # "removed line" doesn't exist in the new file, so "replacement line"
    # takes the very next new-file line number after the context line.
    assert parse_patch_added_lines(patch) == {2}


def test_multiple_hunks_track_line_numbers_independently() -> None:
    patch = (
        "@@ -1,1 +1,2 @@\n"
        " context\n"
        "+added near top\n"
        "@@ -50,1 +51,2 @@\n"
        " other context\n"
        "+added further down"
    )
    assert parse_patch_added_lines(patch) == {2, 52}


def test_no_newline_marker_is_ignored_not_counted_as_a_line() -> None:
    patch = "@@ -1,1 +1,1 @@\n-old\n+new\n\\ No newline at end of file"
    assert parse_patch_added_lines(patch) == {1}
