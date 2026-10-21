import sublime
import sublime_plugin
import time
from .sublime_util import get_selected_lines, move_line_after, insert_line_after, cut_line, get_line, indent_of2

def get_indented_parents(view, line_number):
    start = view.text_point(line_number, 0)
    current = indent_of2(view, view.substr(view.line(start)))

    parents = [(line_number, get_line(view, line_number))]
    row = line_number - 1
    while row >= 0 and current > 0:
        line = view.substr(view.line(view.text_point(row, 0)))
        if line.strip():  # skip blank lines
            indent = indent_of2(view, line)
            if indent < current:
                parents.insert(0, (row, line))
                current = indent
        row -= 1
    return parents

def find_insertion_and_lines_to_insert(view, line_index):
    # TODO: Denne funker ikke i alle cases. Lag ordentlige tester og en ryddig korrekt implementasjon

    text = get_line(view, line_index)

    parents = get_indented_parents(view, line_index)
    
    print(f"line_index: {line_index} parents: {parents}")

    lines = view.lines(sublime.Region(0, view.size()))
    last_line = len(lines) - 1

    if len(parents) == 0:
        print(f"No parents")
        lines_to_insert = [p[1] for p in parents] 
        lines_to_insert.insert(0, "") # Tom linje først for å se pent ut
        return last_line, lines_to_insert

    current_parent_index = 0
    root = -1
    root_parent_i, root_parent_text = parents[0]
    
    for line_region in reversed(lines):
        line = view.rowcol(line_region.begin())[0]

        if line != root_parent_i and root_parent_text == view.substr(line_region):
            print(f"found archived root at {line}")
            root = line
            break

    if root == -1:
        print(f"No archived root")
        lines_to_insert = [p[1] for p in parents] 
        lines_to_insert.insert(0, "") # Tom linje først for å se pent ut
        return last_line, lines_to_insert

    last_found_parent_i = 0
    last_found_parent = root

    for i in range(last_found_parent, len(lines)):
        if last_found_parent_i + 1 > len(parents) - 1: 
            break
        _, next_parent_text = parents[last_found_parent_i + 1]
        if get_line(view, i) == next_parent_text:
            print(f"found: {next_parent_text} at {i}  p_i={last_found_parent_i}")
            last_found_parent = i
            last_found_parent_i += 1

    print(f"last_found_parent: {last_found_parent} ({parents[last_found_parent_i]})")

    insertion_line = last_found_parent
    indent = indent_of2(view, text)

    nof_lines = len(lines)
    while insertion_line + 1 < nof_lines and indent_of2(view, get_line(view, insertion_line + 1)) >= indent:
        insertion_line += 1

    lines_to_insert = [p[1] for p in parents[(last_found_parent_i + 1):]] 

    return insertion_line, lines_to_insert

class ArchiveIndentedCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        lines = get_selected_lines(self.view)

        for i in range(len(lines)):
            line_index = lines[i]
            target_line, lines_to_insert = find_insertion_and_lines_to_insert(self.view, line_index)

            print(f"target_line: {target_line} lines_to_insert: {lines_to_insert}")

            for insert_line in lines_to_insert:
                insert_line_after(self.view, edit, target_line, insert_line)
                target_line += 1

            #cut_line(self.view, edit, line_index)
            #move_line_after(self.view, edit, line_index, target_line)

            # Move all indices of lines that were affected by the move:
            #lines = [x - 1 if line_index <= x <= target_line else x for x in lines]

            # Move target if that was affected:
            #target_line = target_line + 1 if target_line < line_index else target_line


        for line in reversed(lines):
            cut_line(self.view, edit, line)
