"""
Main module for the TerminalView plugin with commands for opening and
initializing a terminal view
"""

import os
import threading
import time

import sublime
import sublime_plugin

from . import sublime_terminal_buffer
from . import linux_pty
from . import utils


class TerminalViewOpen(sublime_plugin.WindowCommand):
    """
    Main entry command for opening a terminal view. Only one instance of this
    class per sublime window. Once a terminal view has been opened the
    TerminalViewCore instance for that view is called to handle everything.
    """
    def run(self, cmd="/bin/bash -l", title="Terminal", cwd=None, syntax=None):
        """
        Open a new terminal view

        Args:
            cmd (str, optional): Shell to execute. Defaults to 'bash -l.
            title (str, optional): Terminal view title. Defaults to 'Terminal'.
            cwd (str, optional): The working dir to start out with. Defaults to
                                 either the currently open file, the currently
                                 open folder, $HOME, or "/", in that order of
                                 precedence. You may pass arbitrary snippet-like
                                 variables.
        """
        if sublime.platform() not in ("linux", "osx"):
            sublime.error_message("TerminalView: Unsupported OS")
            return

        st_vars = self.window.extract_variables()
        if not cwd:
            cwd = "${file_path:${folder}}"
        cwd = sublime.expand_variables(cwd, st_vars)
        if not cwd:
            cwd = os.environ["HOME"]
        if not cwd:
            # Last resort
            cwd = "/"

        args = {"cmd": cmd, "title": title, "cwd": cwd, "syntax": syntax}
        self.window.new_file().run_command("terminal_view_activate", args=args)


class TerminalViewActivate(sublime_plugin.TextCommand):
    def run(self, _, cmd, title, cwd, syntax):
        terminal_view = utils.TerminalViewManager.register(TerminalView(self.view))
        terminal_view.run(cmd, title, cwd, syntax)


class TerminalView:
    """
    Main command to glue all parts together for a single instance of a terminal
    view. For each sublime view an instance of this class exists.
    """
    def __init__(self, view):
        self.view = view

    def run(self, cmd, title, cwd, syntax):
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
        self._console_logger = utils.ConsoleLogger()

        # Initialize the sublime view
        self._terminal_buffer = sublime_terminal_buffer.SublimeTerminalBuffer(self.view, title,
                                                                              self._console_logger,
                                                                              syntax)
        self._terminal_buffer.set_keypress_callback(self.terminal_view_keypress_callback)
        self._terminal_buffer_is_open = True
        self._terminal_rows = 0
        self._terminal_columns = 0

        # Start the underlying shell
        self._shell = linux_pty.LinuxPty(self._cmd.split(), self._cwd)
        self._shell_is_running = True

        # Save the command args in view settings so it can restarted when ST3 is
        # restarted (or when changing back to a project that had a terminal view
        # open)
        args = {"cmd": cmd, "title": title, "cwd": cwd, "syntax": syntax}
        self.view.settings().set("terminal_view_activate_args", args)

        # Start the main loop
        threading.Thread(target=self._main_update_loop).start()

    def terminal_view_keypress_callback(self, key, ctrl=False, alt=False, shift=False, meta=False):
        """
        Callback when a keypress is registered in the Sublime Terminal buffer.

        Args:
            key (str): String describing pressed key. May be a name like 'home'.
            ctrl (boolean, optional)
            alt (boolean, optional)
            shift (boolean, optional)
            meta (boolean, optional)
        """
        self._shell.send_keypress(key, ctrl, alt, shift, meta)

    def _main_update_loop(self):
        """
        This is the main update function. It attempts to run at a certain number
        of frames per second, and keeps input and output synchronized.
        """
        # 30 frames per second should be responsive enough
        ideal_delta = 1.0 / 30.0
        current = time.time()
        while True:
            self._poll_shell_output()
            success = self._terminal_buffer.update_view()
            if not success:
                # Leave view open as we should only get an update if we are
                # reloading the plugin
                self._stop(close_view=False)
                break

            self._resize_screen_if_needed()
            if (not self._terminal_buffer.is_open()) or (not self._shell.is_running()):
                self._stop()
                break

            previous = current
            current = time.time()
            actual_delta = current - previous
            time_left = ideal_delta - actual_delta
            if time_left > 0.0:
                time.sleep(time_left)

    def _poll_shell_output(self):
        """
        Poll the output of the shell
        """
        max_read_size = 4096
        data = self._shell.receive_output(max_read_size)
        if data is not None:
            self._console_logger.log("Got %u bytes of data from shell" % (len(data), ))
            self._terminal_buffer.insert_data(data)

    def _resize_screen_if_needed(self):
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
            self._console_logger.log(log)

            self._terminal_rows = rows
            self._terminal_columns = cols
            self._shell.update_screen_size(self._terminal_rows, self._terminal_columns)
            self._terminal_buffer.update_terminal_size(self._terminal_rows, self._terminal_columns)

    def _stop(self, close_view=True):
        """
        Stop the terminal and close everything down.
        """
        if self._terminal_buffer_is_open and close_view:
            self._terminal_buffer.close()
            self._terminal_buffer_is_open = False

        if self._shell_is_running:
            self._shell.stop()
            self._shell_is_running = False


def plugin_loaded():
    # When the plugin gets loaded everything should be dead so wait a bit to
    # make sure views are ready, then try to restart all sessions.
    sublime.set_timeout(restart_all_terminal_view_sessions, 100)


def restart_all_terminal_view_sessions():
    win = sublime.active_window()
    for view in win.views():
        restart_terminal_view_session(view)


class ProjectSwitchWatcher(sublime_plugin.EventListener):
    def on_load(self, view):
        # On load is called on old terminal views when switching between projects
        restart_terminal_view_session(view)


def restart_terminal_view_session(view):
    settings = view.settings()
    if settings.has("terminal_view_activate_args"):
        view.run_command("terminal_view_clear")
        args = settings.get("terminal_view_activate_args")
        view.run_command("terminal_view_activate", args=args)
