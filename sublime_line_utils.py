import sublime
import sublime_plugin

def get_line(view, row):
    point = view.text_point(row, 0)
    line = view.line(point)
    return view.substr(line)


def indent_of(view, text):
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

def insert_lines_after(view, edit, row, lines_to_insert):
    for insert_line in lines_to_insert:
        insert_line_after(view, edit, row, insert_line)
        row += 1

def move_line_after(view, edit, row, target_row):
    if (row == target_row): 
        return True

    last_row = view.rowcol(view.size())[0] # len(lines) - 1 blir feil hvis siste linje er tom

    if (last_row < row or last_row < target_row):
        sublime.error_message(f"Can not move {row} to {target_row} beyond last line {last_row}") # Skjer også om man flytter siste linje, men siste linje er helt tom
        return False

    text = get_line(view, row)
    insert_line_after(view, edit, target_row, text)

    # Original line is moved one down if it was after the target:
    new_row = row+1 if (row > target_row) else row

    cut_line(view, edit, new_row)

    return True

def move_lines_after(view, edit, rows, target_row):
    for i in range(len(rows)):
        row = rows[i]
        move_line_after(view, edit, row, target_row)

        # Move all rows that were affected by the move:
        rows = [other_row - 1 if row <= other_row <= target_row else other_row for other_row in rows]

        # Move target if that was affected:
        target_row = target_row + 1 if target_row < row else target_row

def get_selected_rows(view):
    rows = set()
    for region in view.sel():
        first_row = view.rowcol(region.begin())[0]
        last_row, last_col = view.rowcol(region.end())

        # A selection that ends at column 0 doesn't include that line
        if last_col == 0 and not region.empty() and last_row > first_row:
            last_row -= 1

        rows.update(range(first_row, last_row + 1))
    return sorted(rows)
