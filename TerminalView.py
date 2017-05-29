import os
import time

import sublime
import sublime_plugin

from . import SublimeTerminalBuffer
from . import LinuxPty
from . import utils

# Todo
# clean global_keypress_callback when terminal is closed
# screen resize test and fix when small col
# colors
# maybe reset terminal on resize ?
# fix word wrap in buffer - turns out we do wrap when window is very small
# allow for customization of what shell (bash, etc.)

# Main entry point for opening a terminal view. Only one instance of this class
# per sublime window. Once a terminal view has been opened the
# TerminalViewCore instance for that view is called to handle everything.
class TerminalViewOpen(sublime_plugin.WindowCommand):
    def run(self):
        if sublime.platform() in ("linux", "osx"):
            win = sublime.active_window()
            view = win.new_file()
            view.run_command("terminal_view_core")
        elif sublime.platform() == "windows":
            sublime.error_message("Windows not supported!")


# Main command to glue everything together. One instance of this per view.
class TerminalViewCore(sublime_plugin.TextCommand):
    def run(self, edit):
        self._terminal_buffer = SublimeTerminalBuffer.SublimeTerminalBuffer(self.view, "bash")
        self._terminal_buffer.set_keypress_callback(self.terminal_view_keypress_callback)
        self._terminal_buffer_is_open = True
        self._terminal_rows = 0
        self._terminal_columns = 0

        # Do an initial buffer draw to fill out terminal with blank spaces
        # before we read initial size
        self._terminal_buffer.update_view()

        if sublime.platform() == "linux":
            self._shell = LinuxPty.LinuxPty("/bin/bash")
        elif sublime.platform() == "osx":
            self._shell = LinuxPty.LinuxPty("/bin/bash", "-l")
        else: # sublime.platform() == "windows"
            sublime.error_message("Windows not supported!")
            return
        self._shell_is_running = True

        # Do initial resize instantly to avoid resizing after first shell prompt
        self._schedule_call_to_check_for_screen_resize(delay=0)
        self._schedule_call_to_poll_shell_output()
        self._schedule_call_to_refresh_terminal_view()
        self._schedule_call_to_check_if_terminal_closed_or_shell_exited()

    def terminal_view_keypress_callback(self, key, ctrl=False, alt=False, shift=False, meta=False):
        self._shell.send_keypress(key, ctrl, alt, shift, meta)

    def _schedule_call_to_check_for_screen_resize(self, delay=250):
        if not self._stopped():
            sublime.set_timeout(self._check_for_screen_resize, delay)

    def _schedule_call_to_poll_shell_output(self):
        if not self._stopped():
            sublime.set_timeout(self._poll_shell_output, 5)

    def _schedule_call_to_refresh_terminal_view(self):
        if not self._stopped():
            sublime.set_timeout(self._refresh_terminal_view, 20)

    def _schedule_call_to_check_if_terminal_closed_or_shell_exited(self):
        if not self._stopped():
            sublime.set_timeout(self._check_if_terminal_closed_or_shell_exited, 100)

    def _poll_shell_output(self):
        max_read_size = 4096
        data = self._shell.receive_output(max_read_size)
        if data is not None:
            utils.log_to_console("Got %u bytes of data from shell" % (len(data), ))
            self._terminal_buffer.insert_data(data)

        self._schedule_call_to_poll_shell_output()

    def _refresh_terminal_view(self):
        self._terminal_buffer.update_view()
        self._schedule_call_to_refresh_terminal_view()

    def _check_if_terminal_closed_or_shell_exited(self):
        self._terminal_buffer_is_open = self._terminal_buffer.is_open()
        self._shell_is_running = self._shell.is_running()

        if (not self._terminal_buffer_is_open) or (not self._shell_is_running):
            self._stop()

        self._schedule_call_to_check_if_terminal_closed_or_shell_exited()

    def _check_for_screen_resize(self):
        (rows, cols) = self._terminal_buffer.view_size()
        row_diff =  abs(self._terminal_rows - rows)
        col_diff =  abs(self._terminal_columns - cols)

        if row_diff or col_diff:
            log = "Changing screen size from (%i, %i) to (%i, %i)" % \
                  (self._terminal_rows, self._terminal_columns, rows, cols)
            utils.log_to_console(log)

            self._terminal_rows = rows
            self._terminal_columns = cols
            self._shell.update_screen_size(self._terminal_rows, self._terminal_columns)
            self._terminal_buffer.update_terminal_size(self._terminal_rows, self._terminal_columns)

        self._schedule_call_to_check_for_screen_resize()

    def _stop(self):
        if self._terminal_buffer_is_open:
            self._terminal_buffer.close()
            self._terminal_buffer_is_open = False

        if self._shell_is_running:
            self._shell.stop()
            self._shell_is_running = False

    def _stopped(self):
        if self._shell_is_running and self._terminal_buffer_is_open:
            return False
        return True
