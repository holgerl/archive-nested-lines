import sublime
import sublime_plugin

def get_line(view, row):
    """Return the text of a 0-based row, or None if out of range."""
    point = view.text_point(row, 0)
    line = view.line(point)
    return view.substr(line)


def indent_of2(view, text):
    tab_size = view.settings().get("tab_size", 4)
    expanded = text.expandtabs(tab_size)
    return len(expanded) - len(expanded.lstrip())

def cut_line(view, edit, row):
    point = view.text_point(row, 0)
    text = view.substr(view.line(point))
    region = view.full_line(point)

    # If the line is an empty line at the end of the file, remove the newline before it
    if not view.substr(region).endswith("\n") and region.begin() > 0:
        region = sublime.Region(region.begin() - 1, region.end())

    view.erase(edit, region)

    return text


def insert_line_after(view, edit, row, text):
    last_row = view.rowcol(view.size())[0] - 1
    if row <= last_row:
        insert_point = view.text_point(row + 1, 0)
        view.insert(edit, insert_point, text + "\n")
    else:
        # Append after the last line, adding a newline in front
        view.insert(edit, view.size(), "\n" + text + "\n")

def move_line_after(view, edit, a, b):
    print(f"moving line {a} to after {b}")

    if (a == b): 
        return True

    last_line = view.rowcol(view.size())[0] # len(lines) - 1 blir feil hvis siste linje er tom

    if (last_line < a or last_line < b):
        sublime.error_message(f"Can not move {a} to {b} beyond last line {last_line}") # Skjer også om man flytter siste linje, men siste linje er helt tom
        return False

    text = get_line(view, a)
    insert_line_after(view, edit, b, text)

    # Original line a is moved one down if a was after b:
    new_a = a+1 if (a > b) else a

    cut_line(view, edit, new_a)

    return True

def move_lines_after(view, edit, lines, target_line):
    for i in range(len(lines)):
        line_index = lines[i]
        move_line_after(view, edit, line_index, target_line)

        # Move all indices of lines that were affected by the move:
        lines = [x - 1 if line_index <= x <= target_line else x for x in lines]

        # Move target if that was affected:
        target_line = target_line + 1 if target_line < line_index else target_line

def get_selected_lines(view):
    rows = set()
    for region in view.sel():
        first_row = view.rowcol(region.begin())[0]
        last_row, last_col = view.rowcol(region.end())

        # A selection that ends at column 0 doesn't include that line
        if last_col == 0 and not region.empty() and last_row > first_row:
            last_row -= 1

        rows.update(range(first_row, last_row + 1))
    return sorted(rows)
