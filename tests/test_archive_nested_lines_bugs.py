"""Known bugs in archive_nested_lines.py not covered by test_archive_nested_lines.py.

Run with: python3 -m unittest discover -s tests   (from the User folder)

Same conventions as test_archive_nested_lines.py: lines to archive are marked
with a trailing "  <<<", and each test states the correct behaviour under
@unittest.expectedFailure. Remove the decorator once the bug is fixed.
"""
import unittest

from fake_sublime import t
from test_archive_nested_lines import archive, without_final_newline


class DataLossBugs(unittest.TestCase):
    def test_line_with_same_text_under_another_root_is_not_deleted(self):
        # BUG: the downward parent search scans the whole rest of the file and
        # matches the line itself ("    x" under Z), so lines_to_insert is
        # empty and x is cut without being copied anywhere.
        before = t("""
            A
                x  <<<

            A
            Z
                x
            """)
        after = t("""
            A

            A
                x
            Z
                x
            """)
        self.assertEqual(archive(before), after)

    @unittest.expectedFailure
    def test_insert_above_a_later_selected_line_does_not_shift_what_is_archived(self):
        # BUG: a2 is inserted above B/b, shifting them down one row. The
        # second selected row then points at B instead of b, so B's hierarchy
        # is archived, the original "B" line is cut, and b is left behind
        # (now looking like a child of the archived A).

        # TODO: Dette er bare når man bruker multiline select, og linjene er ikke sammenhengende?
        # Så det er kanskje litt søkt
        before = t("""
            A
                a  <<<

            A
                old
            B
                b  <<<
            """)
        after = t("""
            A

            A
                old
                a
            B

            B
                b
            """)
        self.assertEqual(archive(before), after)


class WrongPlacementBugs(unittest.TestCase):
    @unittest.expectedFailure
    def test_goes_after_existing_children_separated_by_a_blank_line(self):
        # BUG: the insertion scan treats a blank line as indent 0 and stops
        # there, splitting the archived A's children.

        # TODO: Dette er KANSKJE by design, men man kan jo også se for seg at det ikke var sånn
        before = t("""
            A
                a1  <<<

            A
                old

                old2
            """)
        after = t("""
            A

            A
                old

                old2
                a1
            """)
        self.assertEqual(archive(before), after)


class SelectionEdgeCaseBugs(unittest.TestCase):
    def test_selected_blank_line_does_not_duplicate_its_parent(self):
        # BUG: blank lines are skipped when building the hierarchy, so a
        # selected blank line's hierarchy is its nearest non-blank line above
        # ("    a"), which gets copied into a new archive.
        before = without_final_newline(t("""
            A
                a
              <<<
                b
            B
            """))
        after = t("""
            A
                a
                b
            B""")
        self.assertEqual(archive(before), after)

    def test_selected_blank_line_at_top_of_file_does_not_crash(self):
        # BUG: the hierarchy is empty, so hierarchy[0] raises IndexError.
        before = t("""
              <<<
            A
            """)
        after = t("""
            A
            """)
        self.assertEqual(archive(before), after)


if __name__ == "__main__":
    unittest.main()
