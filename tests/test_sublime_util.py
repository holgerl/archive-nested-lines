"""Run with: python3 -m unittest discover -s tests   (from the User folder)

Uses a minimal fake of the sublime API, so no Sublime Text is needed.
Lives in a subfolder so Sublime doesn't load it as a plugin.
"""
import os
import sys
import types
import textwrap
import unittest


def t(s):
    """Dedent a triple-quoted text block and drop its leading newline."""
    return textwrap.dedent(s).lstrip("\n")


class Region:
    def __init__(self, a, b=None):
        self.a = a
        self.b = a if b is None else b

    def begin(self):
        return min(self.a, self.b)

    def end(self):
        return max(self.a, self.b)

    def empty(self):
        return self.a == self.b

    def __eq__(self, other):
        return (self.a, self.b) == (other.a, other.b)

    def __repr__(self):
        return "Region({}, {})".format(self.a, self.b)


ERRORS = []

sublime_stub = types.ModuleType("sublime")
sublime_stub.Region = Region
sublime_stub.error_message = ERRORS.append
sys.modules["sublime"] = sublime_stub
sys.modules["sublime_plugin"] = types.ModuleType("sublime_plugin")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sublime_util as su  # noqa: E402


class FakeView:
    def __init__(self, text="", tab_size=4):
        self.text = text
        self._tab_size = tab_size
        self._sel = []

    def settings(self):
        return {"tab_size": self._tab_size}

    def size(self):
        return len(self.text)

    def sel(self):
        return self._sel

    def substr(self, region):
        return self.text[region.begin():region.end()]

    def text_point(self, row, col):
        lines = self.text.split("\n")
        if row >= len(lines):
            return len(self.text)
        start = sum(len(l) + 1 for l in lines[:row])
        return start + min(col, len(lines[row]))

    def rowcol(self, point):
        before = self.text[:point]
        row = before.count("\n")
        return row, point - (before.rfind("\n") + 1)

    def line(self, point):
        point = point.begin() if isinstance(point, Region) else point
        start = self.text.rfind("\n", 0, point) + 1
        end = self.text.find("\n", point)
        return Region(start, len(self.text) if end == -1 else end)

    def full_line(self, point):
        r = self.line(point)
        end = r.end() + 1 if r.end() < len(self.text) else r.end()
        return Region(r.begin(), end)

    def insert(self, edit, point, text):
        self.text = self.text[:point] + text + self.text[point:]

    def erase(self, edit, region):
        self.text = self.text[:region.begin()] + self.text[region.end():]


class GetLineTests(unittest.TestCase):
    def test_returns_each_line(self):
        v = FakeView("a\nb\nc")
        self.assertEqual([su.get_line(v, i) for i in range(3)], ["a", "b", "c"])

    def test_empty_line(self):
        self.assertEqual(su.get_line(FakeView("a\n\nb"), 1), "")


class IndentTests(unittest.TestCase):
    def test_spaces(self):
        self.assertEqual(su.indent_of2(FakeView(), "    x"), 4)

    def test_tabs_use_tab_size(self):
        self.assertEqual(su.indent_of2(FakeView(tab_size=4), "\tx"), 4)
        self.assertEqual(su.indent_of2(FakeView(tab_size=2), "\t\tx"), 4)

    def test_none(self):
        self.assertEqual(su.indent_of2(FakeView(), "x"), 0)


class CutLineTests(unittest.TestCase):
    def test_middle_line(self):
        before = t("""
            a
            b
            c
            """)
        after = t("""
            a
            c
            """)
        v = FakeView(before)
        self.assertEqual(su.cut_line(v, None, 1), "b")
        self.assertEqual(v.text, after)

    def test_first_line(self):
        before = t("""
            a
            b
            c
            """)
        after = t("""
            b
            c
            """)
        v = FakeView(before)
        self.assertEqual(su.cut_line(v, None, 0), "a")
        self.assertEqual(v.text, after)

    def test_last_line_without_trailing_newline_removes_preceding_newline(self):
        before = t("""
            a
            b""")
        after = "a"
        v = FakeView(before)
        self.assertEqual(su.cut_line(v, None, 1), "b")
        self.assertEqual(v.text, after)

    def test_trailing_empty_line(self):
        before = "a\n"  # two lines: "a" and an empty last line
        after = "a"
        v = FakeView(before)
        self.assertEqual(su.cut_line(v, None, 1), "")
        self.assertEqual(v.text, after)


class InsertLineAfterTests(unittest.TestCase):
    def test_middle(self):
        before = t("""
            a
            b
            c
            """)
        after = t("""
            a
            X
            b
            c
            """)
        v = FakeView(before)
        su.insert_line_after(v, None, 0, "X")
        self.assertEqual(v.text, after)

    def test_after_last_line_without_trailing_newline(self):
        before = t("""
            a
            b""")
        after = t("""
            a
            b
            X
            """)
        v = FakeView(before)
        su.insert_line_after(v, None, 1, "X")
        self.assertEqual(v.text, after)


class MoveLineAfterTests(unittest.TestCase):
    def test_same_line_is_noop(self):
        before = t("""
            a
            b
            c
            """)
        v = FakeView(before)
        self.assertTrue(su.move_line_after(v, None, 1, 1))
        self.assertEqual(v.text, before)

    def test_move_down(self):
        before = t("""
            a
            b
            c
            d
            """)
        after = t("""
            b
            c
            a
            d
            """)
        v = FakeView(before)
        self.assertTrue(su.move_line_after(v, None, 0, 2))
        self.assertEqual(v.text, after)

    def test_move_up(self):
        before = t("""
            a
            b
            c
            d
            """)
        after = t("""
            a
            d
            b
            c
            """)
        v = FakeView(before)
        self.assertTrue(su.move_line_after(v, None, 3, 0))
        self.assertEqual(v.text, after)

    def test_move_to_end(self):
        before = t("""
            a
            b
            c
            """)
        after = t("""
            b
            c
            a
            """)
        v = FakeView(before)
        self.assertTrue(su.move_line_after(v, None, 0, 2))
        self.assertEqual(v.text, after)

    def test_beyond_last_line_fails(self):
        ERRORS.clear()
        before = t("""
            a
            b
            """)
        v = FakeView(before)
        self.assertFalse(su.move_line_after(v, None, 0, 10))
        self.assertEqual(v.text, before)
        self.assertEqual(len(ERRORS), 1)


class MoveLinesAfterTests(unittest.TestCase):
    def test_move_two_lines_down(self):
        before = t("""
            a
            b
            c
            d
            e
            """)
        after = t("""
            c
            d
            a
            b
            e
            """)
        v = FakeView(before)
        su.move_lines_after(v, None, [0, 1], 3)
        self.assertEqual(v.text, after)

    def test_move_two_lines_up(self):
        before = t("""
            a
            b
            c
            d
            e
            """)
        after = t("""
            a
            d
            e
            b
            c
            """)
        v = FakeView(before)
        su.move_lines_after(v, None, [3, 4], 0)
        self.assertEqual(v.text, after)


class GetSelectedLinesTests(unittest.TestCase):
    def view(self, *regions):
        v = FakeView("aa\nbb\ncc\ndd\n")
        v._sel = list(regions)
        return v

    def test_cursor(self):
        self.assertEqual(su.get_selected_lines(self.view(Region(4))), [1])

    def test_multiline_selection(self):
        self.assertEqual(su.get_selected_lines(self.view(Region(1, 7))), [0, 1, 2])

    def test_selection_ending_at_column_zero_excludes_that_line(self):
        self.assertEqual(su.get_selected_lines(self.view(Region(0, 6))), [0, 1])

    def test_multiple_regions_deduplicated_and_sorted(self):
        v = self.view(Region(7), Region(0), Region(1))
        self.assertEqual(su.get_selected_lines(v), [0, 2])


if __name__ == "__main__":
    unittest.main()
