"""Minimal fake of the Sublime Text API, shared by the tests.

Importing this module installs stub `sublime` and `sublime_plugin` modules and
makes the User package importable as `user_pkg` (archive_nested_lines.py uses a
relative import, so it needs a package).
"""
import importlib
import os
import sys
import textwrap
import types

USER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


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


class TextCommand:
    def __init__(self, view):
        self.view = view


def _install():
    if "sublime" in sys.modules and hasattr(sys.modules["sublime"], "_fake"):
        return
    sublime = types.ModuleType("sublime")
    sublime._fake = True
    sublime.Region = Region
    sublime.error_message = ERRORS.append
    sublime_plugin = types.ModuleType("sublime_plugin")
    sublime_plugin.TextCommand = TextCommand
    sys.modules["sublime"] = sublime
    sys.modules["sublime_plugin"] = sublime_plugin

    pkg = types.ModuleType("user_pkg")
    pkg.__path__ = [USER_DIR]
    sys.modules["user_pkg"] = pkg


_install()

sublime_util = importlib.import_module("user_pkg.sublime_util")
archive_nested_lines = importlib.import_module("user_pkg.archive_nested_lines")


class FakeView:
    def __init__(self, text="", tab_size=4, sel=None):
        self.text = text
        self._tab_size = tab_size
        self._sel = sel or []

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

    def lines(self, region):
        result = []
        start = 0
        for text_line in self.text.split("\n"):
            end = start + len(text_line)
            if end >= region.begin() and start <= region.end():
                result.append(Region(start, end))
            start = end + 1
        return result

    def insert(self, edit, point, text):
        self.text = self.text[:point] + text + self.text[point:]

    def erase(self, edit, region):
        self.text = self.text[:region.begin()] + self.text[region.end():]
