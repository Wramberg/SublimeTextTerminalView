"""
Wrapper module around a Sublime Text 3 view for showing a terminal look-a-like
"""

import sublime
import sublime_plugin
from .TerminalView2 import TerminalView2


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
    def run(self, edit):
        # Lookup the sublime buffer instance for this view
        inst = TerminalView2.from_view(self.view)
        if not inst:
            sublime.error_message("Could not obtain TerminalView instance.")
            return
        copied = sublime.get_clipboard()
        copied = copied.replace("\r\n", "\n")
        inst._shell.send_string(copied)
        # for char in copied:
        #     if char == "\n" or char == "\r":
        #         inst._shell.send_keypress("enter", False, False, False, False)
        #     elif char == "\t":
        #         inst._shell.send_keypress("tab", False, False, False, False)
        #     else:
        #         inst._shell.send_keypress(char, False, False, False, False)


class TerminalViewReporter(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "needs_refocus":
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


class TerminalViewClear(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.set_read_only(False)
        region = sublime.Region(0, self.view.size())
        self.view.erase(edit, region)
        self.view.set_read_only(True)

