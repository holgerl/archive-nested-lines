import sublime
import sublime_plugin
import time
from .sublime_line_utils import get_selected_rows, move_line_after, insert_lines_after, cut_line, get_line, indent_of

def get_indented_hierarchy(view, line_number):
    start = view.text_point(line_number, 0)
    current_indent = 1000000 # Infinity

    parents = []
    row = line_number
    while row >= 0 and current_indent > 0:
        line = view.substr(view.line(view.text_point(row, 0)))
        if line.strip():  # skip blank lines
            indent = indent_of(view, line)
            if indent < current_indent:
                parents.insert(0, (row, line))
                current_indent = indent
        row -= 1
    return parents

def find_insertion_and_lines_to_insert(view, line_index):
    parents = get_indented_hierarchy(view, line_index)
    
    print(f"line_index: {line_index} hierarchy: {parents}")

    lines = view.lines(sublime.Region(0, view.size()))
    last_line = len(lines) - 1

    ## Search bottom up for root parent in archived lines

    current_parent_index = 0
    root = -1
    root_parent_i, root_parent_text = parents[0]
    
    for line_region in reversed(lines):
        line = view.rowcol(line_region.begin())[0]

        if line != root_parent_i and root_parent_text == view.substr(line_region):
            root = line
            break

    if root == -1:
        print(f"No archived root")
        lines_to_insert = [p[1] for p in parents] 
        lines_to_insert.insert(0, "") # Tom linje først for å se pent ut
        return last_line, lines_to_insert

    print(f"found archived root at {root} ({root_parent_text})")

    ## Search downwards for each archived parent in hierarchy

    last_found_parent_i = 0
    last_found_parent = root

    for i in range(last_found_parent, len(lines)):
        if last_found_parent_i + 1 > len(parents) - 1: 
            break
        next_parent_row, next_parent_text = parents[last_found_parent_i + 1]
        if get_line(view, i) == next_parent_text and i != next_parent_row:
            print(f"found intermediate parent: {next_parent_text} at {i}  p_i={last_found_parent_i}")
            last_found_parent = i
            last_found_parent_i += 1

    print(f"last_found_parent: {last_found_parent} ({parents[last_found_parent_i]})")

    ## Insertion line is the line below the last archived parent where indentation decreases

    insertion_line = last_found_parent
    text = get_line(view, line_index)
    indent = indent_of(view, text)

    nof_lines = len(lines)
    while insertion_line + 1 < nof_lines and indent_of(view, get_line(view, insertion_line + 1)) >= indent:
        insertion_line += 1

    ## Lines to insert are the remaining lines in the hierarchy after the last archived parent

    lines_to_insert = [p[1] for p in parents[(last_found_parent_i + 1):]] 

    # TODO: Det skjer rare ting hvis man prøver å archive noe som allerede ligger i archive, og som har en parent som fra før av ligger oppe utenfor archive

    if (insertion_line <= line_index):
        raise AssertionError(f"ERROR: Archive insertion point was not below: {insertion_line} <= {line_index}")

    return insertion_line, lines_to_insert

class ArchiveNestedLinesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        selected_lines = get_selected_rows(self.view)

        for line_index in selected_lines:
            target_line, lines_to_insert = find_insertion_and_lines_to_insert(self.view, line_index)

            print(f"-> target_line: {target_line} lines_to_insert: {lines_to_insert}")
            
            insert_lines_after(self.view, edit, target_line, lines_to_insert)

        for line in reversed(selected_lines):
            cut_line(self.view, edit, line)
