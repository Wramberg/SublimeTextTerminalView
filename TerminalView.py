import os
import threading
import time

import sublime
import sublime_plugin

from . import SublimeTerminalBuffer
from . import LinuxPty
from . import utils


class TerminalViewOpen(sublime_plugin.WindowCommand):
    """
    Main entry command for opening a terminal view. Only one instance of this
    class per sublime window. Once a terminal view has been opened the
    TerminalViewCore instance for that view is called to handle everything.
    """
    def run(self, cmd="/bin/bash -l", title="Terminal",
            cwd="${project_path:${folder:${file_path}}}"):
        """
        Open a new terminal view

        Args:
            cmd (str, optional): Shell to execute. Defaults to 'bash -l.
            title (str, optional): Terminal view title. Defaults to 'Terminal'.
            cwd (str, optional): The working dir to start out with. Defaults to
                                 either the project path, the currently open
                                 folder, the directory of the current file, or
                                 $HOME, in that order of precedence.
        """
        if sublime.platform() not in ("linux", "osx"):
            sublime.error_message("TerminalView: Unsupported OS")
            return

        cwd = sublime.expand_variables(cwd, self.window.extract_variables())
        if not cwd:
            cwd = os.environ["HOME"]

        self.window.new_file().run_command("terminal_view_core",
                args={"cmd": cmd, "title": title, "cwd": cwd})


class TerminalViewCore(sublime_plugin.TextCommand):
    """
    Main command to glue all parts together for a single instance of a terminal
    view. For each sublime view an instance of this class exists.
    """
    def run(self, edit, cmd, title, cwd):
        """
        Initialize the view, in which this command is called, as a terminal
        view.

        Args:
            cmd (str): Command to execute as shell (e.g. 'bash -l').
            title (str): Terminal view title.
            cwd (str): The working directory to start in.
        """
        self._cmd = cmd
        self._cwd = cwd

        # Initialize the sublime view
        self._terminal_buffer = SublimeTerminalBuffer.SublimeTerminalBuffer(self.view, title)
        self.view.settings().add_on_change("_terminal_key", self.terminal_view_keypress_callback)
        self._terminal_buffer_is_open = True
        self._terminal_rows = 0
        self._terminal_columns = 0

        # Start the underlying shell
        self._shell = LinuxPty.LinuxPty(self._cmd.split(), self._cwd)
        self._shell_is_running = True

        # Start the main loop
        threading.Thread(target=self._main_update_loop).start()

    def terminal_view_keypress_callback(self):
        """
        Callback when a keypress is registered in the Sublime Terminal buffer.
        """
        args = self.view.settings().get("_terminal_key")
        if not args: return
        self.view.settings().erase("_terminal_key")
        utils.log_to_console("Keypress: %s" % str(args))
        if args["meta"]:
            sublime.error_message("Terminal View: Meta key is not supported yet")
            return
        self._shell.send_keypress(args["key"], args["ctrl"], args["alt"], args["shift"], args["meta"])

    def _main_update_loop(self):
        """
        This is the main update function. It attempts to run at a certain number
        of frames per second, and keeps input and output synchronized.
        """
        # 30 frames per second should be responsive enough
        IDEAL_DELTA = 1.0 / 30.0
        current = time.time()
        while not self._stopped():
            self._poll_shell_output()
            self._refresh_terminal_view()
            self._check_for_screen_resize()
            self._check_if_terminal_closed_or_shell_exited()
            previous = current
            current = time.time()
            actual_delta = current - previous
            time_left = IDEAL_DELTA - actual_delta
            if time_left > 0.0:
                time.sleep(time_left)

    def _poll_shell_output(self):
        """
        Poll the output of the shell
        """
        max_read_size = 4096
        data = self._shell.receive_output(max_read_size)
        if data is not None:
            utils.log_to_console("Got %u bytes of data from shell" % (len(data), ))
            self._terminal_buffer.insert_data(data)

    def _refresh_terminal_view(self):
        """
        Update the terminal view so its showing the latest data.
        """
        self._terminal_buffer.update_view()

    def _check_for_screen_resize(self):
        """
        Check if the terminal view was resized. If so update the screen size of
        the terminal and notify the shell.
        """

        (rows, cols) = self._terminal_buffer.view_size()
        row_diff = abs(self._terminal_rows - rows)
        col_diff = abs(self._terminal_columns - cols)

        if row_diff or col_diff:
            log = "Changing screen size from (%i, %i) to (%i, %i)" % \
                  (self._terminal_rows, self._terminal_columns, rows, cols)
            utils.log_to_console(log)

            self._terminal_rows = rows
            self._terminal_columns = cols
            self._shell.update_screen_size(self._terminal_rows, self._terminal_columns)
            self._terminal_buffer.update_terminal_size(self._terminal_rows, self._terminal_columns)

    def _check_if_terminal_closed_or_shell_exited(self):
        """
        Check if the terminal was closed or the shell exited. If so stop
        everything.
        """
        self._terminal_buffer_is_open = self._terminal_buffer.is_open()
        self._shell_is_running = self._shell.is_running()

        if (not self._terminal_buffer_is_open) or (not self._shell_is_running):
            self._stop()
            return

    def _stop(self):
        """
        Stop the terminal and close everything down.
        """
        self.view.settings().clear_on_change("_terminal_key")
        if self._terminal_buffer_is_open:
            self._terminal_buffer.close()
            self._terminal_buffer_is_open = False

        if self._shell_is_running:
            self._shell.stop()
            self._shell_is_running = False

    def _stopped(self):
        """
        Check if the terminal or shell are stopped.
        """
        if not self._shell_is_running:
            return True

        if not self._terminal_buffer_is_open:
            return True

        return False
