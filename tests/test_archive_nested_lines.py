"""Tests for archive_nested_lines.py.

Run with: python3 -m unittest discover -s tests   (from the User folder)

Each test shows the document as text before and after archiving. Lines to
archive are marked with a trailing "  <<<" in the `before` text; the marker is
stripped before the command runs, so it never appears in the document.

Tests decorated with @unittest.expectedFailure document known bugs: they state
the correct behaviour, and will start "unexpectedly succeeding" once fixed
(then just remove the decorator).
"""
import contextlib
import io
import unittest
from collections import Counter

from fake_sublime import FakeView, Region, archive_nested_lines as ai, t

MARK = "  <<<"


def marked(text):
    """Split marked text into (clean text, rows that carried the marker)."""
    rows = []
    clean = []
    for row, line in enumerate(text.split("\n")):
        if line.endswith(MARK):
            rows.append(row)
            line = line[:-len(MARK)]
        clean.append(line)
    return "\n".join(clean), rows


def archive(before):
    """Run the archive command on `before` and return the resulting text."""
    text, rows = marked(before)
    view = FakeView(text)
    view._sel = [Region(view.text_point(row, 0)) for row in rows]
    with contextlib.redirect_stdout(io.StringIO()):
        ai.ArchiveNestedLinesCommand(view).run(None)
    return view.text


def without_final_newline(text):
    return text.rstrip("\n")


class ArchiveIntoExistingArchiveTests(unittest.TestCase):
    """The archive (a copy of the parent lines at the bottom) already exists."""

    def test_nested_line_is_appended_under_its_existing_parent(self):
        before = t("""
            A
                a1
                a2  <<<
            B
                b1

            A
                old
            """)
        after = t("""
            A
                a1
            B
                b1

            A
                old
                a2
            """)
        self.assertEqual(archive(before), after)

    def test_goes_after_all_existing_children_including_deeper_ones(self):
        before = t("""
            A
                a1
                a2  <<<

            A
                old
                    oldkid
            """)
        after = t("""
            A
                a1

            A
                old
                    oldkid
                a2
            """)
        self.assertEqual(archive(before), after)

    def test_stops_before_next_top_level_block(self):
        before = t("""
            A
                a1
                a2  <<<

            A
                old
            Z
                z
            """)
        after = t("""
            A
                a1

            A
                old
                a2
            Z
                z
            """)
        self.assertEqual(archive(before), after)

    def test_deep_line_whose_full_parent_path_exists(self):
        before = t("""
            A
                B
                    c
                    d  <<<

            A
                B
                    old
            """)
        after = t("""
            A
                B
                    c

            A
                B
                    old
                    d
            """)
        self.assertEqual(archive(before), after)

    def test_only_part_of_the_parent_path_exists(self):
        before = t("""
            A
                B
                    c  <<<

            A
            """)
        after = t("""
            A
                B

            A
                B
                    c
            """)
        self.assertEqual(archive(before), after)

    def test_several_lines_with_the_same_parent_keep_their_order(self):
        before = t("""
            A
                a1  <<<
                a2  <<<
                a3

            A
                old
            """)
        after = t("""
            A
                a3

            A
                old
                a1
                a2
            """)
        self.assertEqual(archive(before), after)

    def test_lines_with_different_parents(self):
        before = t("""
            A
                a  <<<
            B
                b  <<<

            A
                old
            B
                oldb
            """)
        after = t("""
            A
            B

            A
                old
                a
            B
                oldb
                b
            """)
        self.assertEqual(archive(before), after)

    def test_top_level_line_equal_to_existing_archive_root_is_merged(self):
        before = t("""
            x
            z  <<<

            z
                old
            """)
        after = t("""
            x

            z
                old
            """)
        self.assertEqual(archive(before), after)

    def test_tab_indentation(self):
        before = t("""
            A
                a1
                a2  <<<

            A
                old
            """).replace("    ", "\t")
        after = t("""
            A
                a1

            A
                old
                a2
            """).replace("    ", "\t")
        self.assertEqual(archive(before), after)

    def test_archive_without_trailing_newline(self):
        before = without_final_newline(t("""
            A
                a1
                a2  <<<

            A
                old
            """))
        after = t("""
            A
                a1

            A
                old
                a2
            """)
        self.assertEqual(archive(before), after)

    def test_unmarked_lines_are_never_touched(self):
        before = t("""
            A
                a1
                a2  <<<
                a3
                    deep

            A
                old
            """)
        after = t("""
            A
                a1
                a3
                    deep

            A
                old
                a2
            """)
        self.assertEqual(archive(before), after)


class ArchiveCreatingNewArchiveTests(unittest.TestCase):
    """There is no archive yet: it is created at the bottom after a blank line."""

    def test_nested_line_gets_its_parent_copied_to_new_archive(self):
        before = without_final_newline(t("""
            A
                a  <<<
            B
            """))
        after = t("""
            A
            B

            A
                a
            """)
        self.assertEqual(archive(before), after)

    def test_all_parents_are_copied_outermost_first(self):
        before = without_final_newline(t("""
            A
                B
                    c  <<<
                    d
                e
            """))
        after = t("""
            A
                B
                    d
                e

            A
                B
                    c
            """)
        self.assertEqual(archive(before), after)

    def test_several_lines_with_same_parent_share_one_copy_of_it(self):
        before = without_final_newline(t("""
            A
                a1  <<<
                a2  <<<
            B
            """))
        after = t("""
            A
            B

            A
                a1
                a2
            """)
        self.assertEqual(archive(before), after)

    def test_top_level_line_is_moved_to_new_archive(self):
        before = without_final_newline(t("""
            a
            b  <<<
            c
            """))
        after = t("""
            a
            c

            b
            """)
        self.assertEqual(archive(before), after)

    def test_single_line_file(self):
        self.assertEqual(archive("a" + MARK), "\na\n")

    @unittest.expectedFailure
    def test_file_with_trailing_newline_gets_one_blank_separator_line(self):
        # BUG: two blank lines are inserted, because insert_line_after adds a
        # newline in front when appending after the (empty) last line.
        before = t("""
            A
                a  <<<
            B
            """)
        after = t("""
            A
            B

            A
                a
            """)
        self.assertEqual(archive(before), after)

    @unittest.expectedFailure
    def test_second_new_root_gets_one_blank_separator_line(self):
        # BUG: same cause as above, hits the second root as the first insert
        # leaves the file ending in a newline.
        before = without_final_newline(t("""
            A
                a  <<<
            B
                b  <<<
            C
            """))
        after = t("""
            A
            B
            C

            A
                a

            B
                b
            """)
        self.assertEqual(archive(before), after)


class ArchiveEdgeCaseTests(unittest.TestCase):
    def test_no_selection_changes_nothing(self):
        before = t("""
            A
                a
            B
            """)
        self.assertEqual(archive(before), before)

    def test_last_line_of_file_can_be_archived(self):
        before = without_final_newline(t("""
            A
                a1
                a2  <<<
            """))
        after = t("""
            A
                a1

            A
                a2
            """)
        self.assertEqual(archive(before), after)

    @unittest.expectedFailure
    def test_child_with_same_name_under_another_top_level_block(self):
        # BUG: the parent lookup scans the rest of the file and matches
        # "    B" under Z, so c ends up in Z instead of in the archived A.
        before = t("""
            A
                B
                    c  <<<

            A
            Z
                B
            """)
        after = t("""
            A
                B

            A
                B
                    c
            Z
                B
            """)
        self.assertEqual(archive(before), after)

    @unittest.expectedFailure
    def test_line_is_never_lost_when_parent_text_is_duplicated(self):
        # BUG: the lookup finds the very line being archived as if it were
        # already in the archive, so it is deleted without being copied.
        before = t("""
            A
                a
            A
                b  <<<
            """)
        before_lines = Counter(l for l in marked(before)[0].split("\n") if l.strip())
        after_lines = Counter(l for l in archive(before).split("\n") if l.strip())
        self.assertEqual(before_lines - after_lines, Counter())

    @unittest.expectedFailure
    def test_line_is_never_lost_when_it_has_an_earlier_twin_parent(self):
        before = t("""
            A
                old

            A
                a  <<<
            """)
        before_lines = Counter(l for l in marked(before)[0].split("\n") if l.strip())
        after_lines = Counter(l for l in archive(before).split("\n") if l.strip())
        self.assertEqual(before_lines - after_lines, Counter())


class GetIndentedHierarchyTests(unittest.TestCase):
    """get_indented_hierarchy returns [(row, text)] outermost first, ending with the line itself."""

    DOC = t("""
        A
            B
                c

                d
            e
        F
        """)

    def parents(self, row, text=None):
        return ai.get_indented_hierarchy(FakeView(text or self.DOC), row)

    def test_top_level_line_has_only_itself(self):
        self.assertEqual(self.parents(0), [(0, "A")])

    def test_nested_line(self):
        self.assertEqual(self.parents(2), [(0, "A"), (1, "    B"), (2, "        c")])

    def test_blank_lines_between_are_skipped(self):
        self.assertEqual(self.parents(4), [(0, "A"), (1, "    B"), (4, "        d")])

    def test_siblings_are_not_parents(self):
        self.assertEqual(self.parents(5), [(0, "A"), (5, "    e")])

    def test_following_top_level_line_does_not_include_earlier_blocks(self):
        self.assertEqual(self.parents(6), [(6, "F")])

    def test_tabs_count_as_tab_size_spaces(self):
        text = "A\n\tB\n\t\tc\n"
        self.assertEqual(self.parents(2, text), [(0, "A"), (1, "\tB"), (2, "\t\tc")])

    def test_mixed_tabs_and_spaces(self):
        text = "A\n    B\n\t\tc\n"
        self.assertEqual(self.parents(2, text), [(0, "A"), (1, "    B"), (2, "\t\tc")])


class FindInsertionTests(unittest.TestCase):
    """find_insertion_and_lines_to_insert returns (row to insert after, lines to insert)."""

    def find(self, text, row):
        with contextlib.redirect_stdout(io.StringIO()):
            return ai.find_insertion_and_lines_to_insert(FakeView(text), row)

    def test_existing_parent_means_only_the_line_itself_is_inserted(self):
        text = t("""
            A
                a

            A
                old
            """)
        self.assertEqual(self.find(text, 1), (4, ["    a"]))

    def test_new_archive_appends_blank_line_and_all_parents_after_last_line(self):
        text = "A\n    a"
        self.assertEqual(self.find(text, 1), (1, ["", "A", "    a"]))


if __name__ == "__main__":
    unittest.main()
