import sublime
import sublime_plugin

from . import pyte
from . import utils

class SublimeTerminalBuffer():
    def __init__(self, sublime_view, title):
        self._view = sublime_view
        sublime_view.set_name(title)
        sublime_view.set_scratch(True)
        sublime_view.set_read_only(True)
        sublime_view.settings().set("gutter", False)
        sublime_view.settings().set("highlight_line", False)
        sublime_view.settings().set("auto_complete_commit_on_tab", False)
        sublime_view.settings().set("draw_centered", False)
        sublime_view.settings().set("word_wrap", False)
        sublime_view.settings().set("auto_complete", False)
        sublime_view.settings().set("draw_white_space", "none")
        sublime_view.settings().set("draw_indent_guides", False)
        sublime_view.settings().set("caret_style", "blink")
        sublime_view.settings().add_on_change('color_scheme', lambda: set_color_scheme(sublime_view))

        # Mark in the views private settings that this is a terminal view so we
        # can use this as context in the keymap
        sublime_view.settings().set("terminal_view", True)
        sublime.active_window().focus_view(sublime_view)

        # Start out with a large terminal to ensure ST draws scrollbars etc. If
        # we do not do this we will end up resizing terminal first time its
        # rendered
        self._bytestream = pyte.ByteStream()
        self._screen = pyte.DiffScreen(800, 240)
        self._bytestream.attach(self._screen)

    def insert_data(self, data):
        self._bytestream.feed(data)

    def update_view(self):
        if len(self._screen.dirty) > 0:
            update = {"lines": list(self._screen.dirty), "display": self._screen.display}
            self._view.run_command("terminal_view_update_lines", update)

        self._update_cursor()
        self._screen.dirty.clear()

    def is_open(self):
        """
        Check if the terminal view is open.
        """
        if self._view.window() is not None:
            return True

        return False

    def close(self):
        if self.is_open():
            sublime.active_window().focus_view(self._view)
            sublime.active_window().run_command("close_file")

    def update_terminal_size(self, nb_rows, nb_cols):
        self._screen.resize(lines=nb_rows, columns=nb_cols)

    def view_size(self):
        view = self._view
        (pixel_width, pixel_height) = view.viewport_extent()
        pixel_per_line = view.line_height()
        pixel_per_char = view.em_width()

        if pixel_per_line == 0 or pixel_per_char == 0:
            return (0, 0)

        nb_columns = int(pixel_width/pixel_per_char) - 2
        if nb_columns < 40:
            nb_columns = 40

        nb_rows = int(pixel_height/pixel_per_line)
        if nb_rows < 20:
            nb_rows = 20

        return (nb_rows, nb_columns)

    def _update_cursor(self):
        cursor = self._screen.cursor
        if cursor:
            self._view.run_command("terminal_view_move_cursor", {"cursor_x": cursor.x, "cursor_y": cursor.y})


class TerminalViewMoveCursor(sublime_plugin.TextCommand):
    def run(self, edit, cursor_x, cursor_y):
        tp = self.view.text_point(cursor_y, cursor_x)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(tp, tp))


class TerminalViewKeypress(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        settings = self.view.settings()
        settings.set("_terminal_key", kwargs)


class TerminalViewClear(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.erase(edit, sublime.Region(0, self.view.size()))


class TerminalViewUpdateLines(sublime_plugin.TextCommand):
    def run(self, edit, lines, display):
        self.view.set_read_only(False)
        for line_no in sorted(lines):
            try:
                content = display[line_no]
            except:
                return
            p = self.view.text_point(line_no, 0)
            line_region = self.view.line(p)
            if line_region.empty():
                self.view.replace(edit, line_region, content + "\n")
            else:
                self.view.replace(edit, line_region, content)
        self.view.set_read_only(True)

def set_color_scheme(view):
    """
    Set color scheme for view
    """
    color_scheme = "Packages/TerminalView/TerminalView.hidden-tmTheme"

    # Check if user color scheme exists
    try:
        sublime.load_resource("Packages/User/TerminalView.hidden-tmTheme")
        color_scheme = "Packages/User/TerminalView.hidden-tmTheme"
    except:
        pass

    if view.settings().get('color_scheme') != color_scheme:
        view.settings().set('color_scheme', color_scheme)
