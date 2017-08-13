"""
Wrapper module around a Sublime Text 3 view for showing a terminal look-a-like
"""
import collections
import time

import sublime
import sublime_plugin

from . import gateone_terminal_emulator
from . import pyte_terminal_emulator
from . import utils
from . import sublime_view_cache


class SublimeBufferManager():
    """
    A manager to control all SublimeBuffer instances so they can be looked up
    based on the sublime view they are governing.
    """
    @classmethod
    def register(cls, uid, sublime_buffer):
        if not hasattr(cls, "buffers"):
            cls.buffers = {}
        cls.buffers[uid] = sublime_buffer

    @classmethod
    def deregister(cls, uid):
        if hasattr(cls, "buffers"):
            del cls.buffers[uid]

    @classmethod
    def load_from_id(cls, uid):
        if hasattr(cls, "buffers") and uid in cls.buffers:
            return cls.buffers[uid]
        else:
            raise Exception("[terminal_view error] Sublime buffer not found")


class SublimeTerminalBuffer():
    def __init__(self, sublime_view, title, syntax_file=None):
        self._view = sublime_view
        self._view.set_name(title)
        self._view.set_scratch(True)
        self._view.set_read_only(True)
        self._view.settings().set("gutter", False)
        self._view.settings().set("highlight_line", False)
        self._view.settings().set("auto_complete_commit_on_tab", False)
        self._view.settings().set("draw_centered", False)
        self._view.settings().set("word_wrap", False)
        self._view.settings().set("auto_complete", False)
        self._view.settings().set("draw_white_space", "none")
        self._view.settings().set("draw_indent_guides", False)
        self._view.settings().set("caret_style", "blink")
        self._view.settings().set("scroll_past_end", False)
        self._view.settings().add_on_change('color_scheme', lambda: set_color_scheme(self._view))

        if syntax_file is not None:
            self._view.set_syntax_file("Packages/User/" + syntax_file)

        # Mark in the views private settings that this is a terminal view so we
        # can use this as context in the keymap
        self._view.settings().set("terminal_view", True)

        settings = sublime.load_settings('TerminalView.sublime-settings')
        self._show_colors = settings.get("terminal_view_show_colors", False)
        self._right_margin = settings.get("terminal_view_right_margin", 3)
        self._bottom_margin = settings.get("terminal_view_bottom_margin", 0)

        # Use pyte as underlying terminal emulator
        hist = settings.get("terminal_view_scroll_history", 1000)
        ratio = settings.get("terminal_view_scroll_ratio", 0.5)
        self._term_emulator = pyte_terminal_emulator.PyteTerminalEmulator(80, 24, hist, ratio)

        self._keypress_callback = None
        self._write_process_input_callback = None
        self._view_content_cache = sublime_view_cache.SublimeViewContentCache()
        self._view_region_cache = sublime_view_cache.SublimeViewRegionCache()

        # Register the new instance of the sublime buffer class so other
        # commands can look it up when they are called in the same sublime view
        SublimeBufferManager.register(sublime_view.id(), self)

    def __del__(self):
        utils.ConsoleLogger.log("Sublime buffer instance deleted")

    def set_write_process_input_callback(self, callback):
        self._term_emulator._screen.write_process_input = callback

    def set_keypress_callback(self, callback):
        self._keypress_callback = callback

    def keypress_callback(self):
        return self._keypress_callback

    def view_region_cache(self):
        return self._view_region_cache

    def view_content_cache(self):
        return self._view_content_cache

    def colors_enabled(self):
        return self._show_colors

    def terminal_emulator(self):
        return self._term_emulator

    def insert_data(self, data):
        start = time.time()
        self._term_emulator.feed(data)
        t = time.time() - start
        utils.ConsoleLogger.log("Updated terminal emulator in %.3f ms" % (t * 1000.))

    def update_view(self):
        self._scroll_terminal_if_requested()
        if self.terminal_emulator().modified():
            self._view.run_command("terminal_view_update")

    def is_open(self):
        return self._view.is_valid()

    def deactivate(self):
        self._view.settings().set("terminal_view", False)
        self.update_view()
        self._keypress_callback = None
        SublimeBufferManager.deregister(self._view.id())

    def close(self):
        if self.is_open():
            sublime.active_window().focus_view(self._view)
            sublime.active_window().run_command("close_file")

    def update_terminal_size(self, nb_rows, nb_cols):
        # Make sure all content beyond the new number of rows is deleted
        if nb_rows < self._term_emulator.nb_lines():
            start, _ = self.view_content_cache().get_line_start_and_end_points(nb_rows)
            self._view.run_command("terminal_view_clear", args={"start": start})

        self._term_emulator.resize(nb_rows, nb_cols)

    def view_size(self):
        view = self._view
        (pixel_width, pixel_height) = view.viewport_extent()
        pixel_per_line = view.line_height()
        pixel_per_char = view.em_width()

        if pixel_per_line == 0 or pixel_per_char == 0:
            return (0, 0)

        # Subtract one to avoid any wrapping issues
        nb_columns = int(pixel_width / pixel_per_char) - self._right_margin
        if nb_columns < 1:
            nb_columns = 1

        nb_rows = int(pixel_height / pixel_per_line) - self._bottom_margin
        if nb_rows < 1:
            nb_rows = 1

        return (nb_rows, nb_columns)

    def _scroll_terminal_if_requested(self):
        scroll_request = self._view.settings().get("terminal_view_scroll", None)
        if scroll_request is not None:
            index = scroll_request[0]
            direction = scroll_request[1]
            if index == "line":
                if direction == "up":
                    self.terminal_emulator().prev_line()
                else:
                    self.terminal_emulator().next_line()
            else:
                if direction == "up":
                    self.terminal_emulator().prev_page()
                else:
                    self.terminal_emulator().next_page()

            self._view.settings().set("terminal_view_scroll", None)


class TerminalViewScroll(sublime_plugin.TextCommand):
    def run(self, _, forward=False, line=False):
        # Mark in view to request a scroll in the thread that handles the
        # updates. Note lines are NOT supported at the moment.
        if line:
            scroll_request = ("line", )
        else:
            scroll_request = ("page", )

        if not forward:
            scroll_request = scroll_request + ("up", )
        else:
            scroll_request = scroll_request + ("down", )

        self.view.settings().set("terminal_view_scroll", scroll_request)


class TerminalViewKeypress(sublime_plugin.TextCommand):
    def __init__(self, view):
        super().__init__(view)
        self._sub_buffer = None

    def run(self, _, **kwargs):
        # Lookup the sublime buffer instance for this view the first time this
        # command is called
        if self._sub_buffer is None:
            self._sub_buffer = SublimeBufferManager.load_from_id(self.view.id())

        if type(kwargs["key"]) is not str:
            sublime.error_message("Terminal View: Got keypress with non-string key")
            return

        if "meta" in kwargs and kwargs["meta"]:
            sublime.error_message("Terminal View: Meta key is not supported yet")
            return

        if "meta" not in kwargs:
            kwargs["meta"] = False
        if "alt" not in kwargs:
            kwargs["alt"] = False
        if "ctrl" not in kwargs:
            kwargs["ctrl"] = False
        if "shift" not in kwargs:
            kwargs["shift"] = False

        # Lookup the sublime buffer instance for this view
        sublime_buffer = SublimeBufferManager.load_from_id(self.view.id())
        keypress_cb = sublime_buffer.keypress_callback()
        app_mode = sublime_buffer.terminal_emulator().application_mode_enabled()
        if keypress_cb:
            keypress_cb(kwargs["key"], kwargs["ctrl"], kwargs["alt"],
                        kwargs["shift"], kwargs["meta"], app_mode)


class TerminalViewCopy(sublime_plugin.TextCommand):
    def run(self, edit):
        # Get selected region or use line that cursor is on if nothing is
        # selected
        selected_region = self.view.sel()[0]
        if selected_region.empty():
            selected_region = self.view.line(selected_region)

        # Clean the selected text and move it into clipboard
        selected_text = self.view.substr(selected_region)
        selected_lines = selected_text.split("\n")
        clean_contents_to_copy = ""
        for line in selected_lines:
            clean_contents_to_copy = clean_contents_to_copy + line.rstrip() + "\n"

        sublime.set_clipboard(clean_contents_to_copy[:-1])


class TerminalViewPaste(sublime_plugin.TextCommand):
    def run(self, edit, bracketed=False):
        # Lookup the sublime buffer instance for this view
        sub_buffer = SublimeBufferManager.load_from_id(self.view.id())
        keypress_cb = sub_buffer.keypress_callback()
        if not keypress_cb:
            return

        # Check if bracketed paste mode is enabled
        bracketed = bracketed or sub_buffer.terminal_emulator().bracketed_paste_mode_enabled()
        if bracketed:
            keypress_cb("bracketed_paste_mode_start")

        copied = sublime.get_clipboard()
        copied = copied.replace("\r\n", "\n")
        for char in copied:
            if char == "\n" or char == "\r":
                keypress_cb("enter")
            elif char == "\t":
                keypress_cb("tab")
            else:
                keypress_cb(char)

        if bracketed:
            keypress_cb("bracketed_paste_mode_end")


class TerminalViewReporter(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "terminal_view_needs_refocus":
            cursor_pos = view.settings().get("terminal_view_last_cursor_pos")
            if cursor_pos:
                if len(view.sel()) != 1 or not view.sel()[0].empty():
                    return operand

                row, col = view.rowcol(view.sel()[0].end())
                return (row == cursor_pos[0] and col == cursor_pos[1]) != operand


class TerminalViewRefocus(sublime_plugin.TextCommand):
    def run(self, _):
        cursor_pos = self.view.settings().get("terminal_view_last_cursor_pos")
        tp = self.view.text_point(cursor_pos[0], cursor_pos[1])
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(tp, tp))


class TerminalViewUpdate(sublime_plugin.TextCommand):
    def __init__(self, view):
        super().__init__(view)
        self._sub_buffer = None

    def run(self, edit):
        # Lookup the sublime buffer instance for this view the first time this
        # command is called
        if self._sub_buffer is None:
            self._sub_buffer = SublimeBufferManager.load_from_id(self.view.id())

        # Update dirty lines in buffer if there are any
        dirty_lines = self._sub_buffer.terminal_emulator().dirty_lines()
        if len(dirty_lines) > 0:
            self._update_viewport_position()

            # Invalidate the last cursor position when dirty lines are updated
            self.view.settings().set("terminal_view_last_cursor_pos", None)

            # Generate color map
            color_map = {}
            if self._sub_buffer.colors_enabled():
                start = time.time()
                color_map = self._sub_buffer.terminal_emulator().color_map(dirty_lines.keys())
                t = time.time() - start
                utils.ConsoleLogger.log("Generated color map in %.3f ms" % (t * 1000.))

            # Update the view
            start = time.time()
            self._update_lines(edit, dirty_lines, color_map)
            t = time.time() - start
            utils.ConsoleLogger.log("Updated ST3 view in %.3f ms" % (t * 1000.))

        # Update cursor last to avoid a selection blinking at the top of the
        # terminal when starting or when a new prompt is being drawn at the
        # bottom
        self._update_cursor()

        # Clear dirty lines (and modified flag)
        self._sub_buffer.terminal_emulator().clear_dirty()

    def _update_viewport_position(self):
        self.view.set_viewport_position((0, 0), animate=False)

    def _update_cursor(self):
        cursor_pos = self._sub_buffer.terminal_emulator().cursor()
        last_cursor_pos = self.view.settings().get("terminal_view_last_cursor_pos")
        if last_cursor_pos and last_cursor_pos[0] == cursor_pos[0] and last_cursor_pos[1] == cursor_pos[1]:
            return

        tp = self.view.text_point(cursor_pos[0], cursor_pos[1])
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(tp, tp))
        self.view.settings().set("terminal_view_last_cursor_pos", cursor_pos)

    def _update_lines(self, edit, dirty_lines, color_map):
        self.view.set_read_only(False)
        lines = dirty_lines.keys()
        for line_no in sorted(lines):
            # Clear any colors on the line
            self._remove_color_regions_on_line(line_no)

            # Update the line
            self._update_line_content(edit, line_no, dirty_lines[line_no])

            # Apply colors to the line if there are any on it
            if line_no in color_map:
                self._update_line_colors(line_no, color_map[line_no])

        self.view.set_read_only(True)

    def _remove_color_regions_on_line(self, line_no):
        view_region_cache = self._sub_buffer.view_region_cache()
        if view_region_cache.has_line(line_no):
            region_keys = view_region_cache.get_line(line_no)
            for key in region_keys:
                self.view.erase_regions(key)
            view_region_cache.delete_line(line_no)

    def _update_line_content(self, edit, line_no, content):
        # Note this function has been optimized quite a bit. Calls to the ST3
        # API has been left out on purpose as they are slower than the
        # alternative.

        # We need to add a newline otherwise ST3 does not break the line
        content_w_newline = content + "\n"

        # Check in our local buffer that the content line is different from what
        # we are already showing - otherwise we can stop now
        view_content_cache = self._sub_buffer.view_content_cache()
        if view_content_cache.has_line(line_no):
            if view_content_cache.get_line(line_no) == content_w_newline:
                return

        # Content is different - make ST3 region that spans the line. Start by
        # geting start and end point of the line
        line_start, line_end = view_content_cache.get_line_start_and_end_points(line_no)

        # Make region spanning entire line (including any newline at the end)
        line_region = sublime.Region(line_start, line_end)
        self.view.replace(edit, line_region, content_w_newline)
        view_content_cache.update_line(line_no, content_w_newline)

    def _update_line_colors(self, line_no, line_color_map):
        # Note this function has been optimized quite a bit. Calls to the ST3
        # API has been left out on purpose as they are slower than the
        # alternative.
        view_region_cache = self._sub_buffer.view_region_cache()
        view_content_cache = self._sub_buffer.view_content_cache()

        for idx, field in line_color_map.items():
            length = field["field_length"]
            color_scope = "terminalview.%s_%s" % (field["color"][0], field["color"][1])

            # Get text point where color should start
            line_start, _ = view_content_cache.get_line_start_and_end_points(line_no)
            color_start = line_start + idx

            # Make region that should be colored
            buffer_region = sublime.Region(color_start, color_start + length)
            region_key = "%i,%s" % (line_no, idx)

            # Add the region
            flags = sublime.DRAW_NO_OUTLINE | sublime.PERSISTENT
            self.view.add_regions(region_key, [buffer_region], color_scope, flags=flags)
            view_region_cache.add(line_no, region_key)


class TerminalViewClear(sublime_plugin.TextCommand):
    def run(self, edit, start=0, end=None):
        if end is None:
            end = self.view.size()

        self.view.set_read_only(False)
        region = sublime.Region(start, end)
        self.view.erase(edit, region)
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
