"""
Main module for the TerminalView plugin with commands for opening and
initializing a terminal view
"""

import os
import threading
import time
import shlex  # for split()

import sublime
import sublime_plugin

from . import sublime_terminal_buffer
from . import linux_pty
from . import utils


class TerminalViewManager():
    """
    A manager to control all TerminalView instances so they can be looked up
    based on the sublime view they are governing.
    """
    @classmethod
    def register(cls, uid, term_view):
        if not hasattr(cls, "term_views"):
            cls.term_views = {}
        cls.term_views[uid] = term_view

    @classmethod
    def deregister(cls, uid):
        if hasattr(cls, "term_views"):
            del cls.term_views[uid]

    @classmethod
    def load_from_id(cls, uid):
        if hasattr(cls, "term_views") and uid in cls.term_views:
            return cls.term_views[uid]
        else:
            return None


class TerminalViewOpen(sublime_plugin.WindowCommand):
    """
    Main entry command for opening a terminal view. Only one instance of this
    class per sublime window. Once a terminal view has been opened the
    TerminalViewActivate instance for that view is called to handle everything.
    """
    def run(self,
            cmd=["/bin/bash", "-l"],
            title="Terminal",
            cwd=None,
            syntax=None,
            keep_open=False):
        """
        Open a new terminal view

        Args:
            cmd (str or list of str, optional): Shell to execute. Defaults to ["bin/bash", "-l"].
            title (str, optional): Terminal view title. Defaults to 'Terminal'.
            cwd (str, optional): The working dir to start out with. Defaults to either the
                                 currently open file, the currently open folder, $HOME, or "/", in
                                 that order of precedence. You may pass arbitrary snippet-like
                                 variables.
            syntax (str, optional): Syntax file to use in the view.
            keep_open (bool, optional): Keep view open after cmd exits.
        """
        if sublime.platform() not in ("linux", "osx"):
            sublime.error_message("TerminalView: Unsupported OS")
            return

        st_vars = self.window.extract_variables()
        if not cwd:
            cwd = "${file_path:${folder}}"
        cwd = sublime.expand_variables(cwd, st_vars)
        if not cwd:
            cwd = os.environ.get("HOME", None)
        if not cwd:
            # Last resort
            cwd = "/"

        # Make sure the cmd is a list of strings.
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        elif isinstance(cmd, list):
            pass
        else:
            sublime.error_message('The "cmd" argument must be either a string or a list of strings.')
            return

        args = {"cmd": cmd, "title": title, "cwd": cwd, "syntax": syntax, "keep_open": keep_open}
        self.window.new_file().run_command("terminal_view_activate", args=args)


class TerminalViewActivate(sublime_plugin.TextCommand):
    def run(self, _, cmd, title, cwd, syntax, keep_open):
        terminal_view = TerminalView(self.view)
        try:
            terminal_view.run(cmd, title, cwd, syntax, keep_open)
        except FileNotFoundError:
            # Note that this exception is only thrown from within LinuxPty,
            # at which point the registration to the manager hasn't happened
            # yet, so we don't have to deregister.
            print("TerminalView: Failed to open {}. Reverting to home/root dir.".format(cwd))
            cwd = os.environ.get("HOME", None)
            if not cwd:
                cwd = "/"
            terminal_view.run(cmd, title, cwd, syntax, keep_open)


class TerminalView:
    """
    Main class to glue all parts together for a single instance of a terminal
    view.
    """
    def __init__(self, view):
        self.view = view

    def __del__(self):
        utils.ConsoleLogger.log("Terminal view instance deleted")

    def run(self, cmd, title, cwd, syntax, keep_open):
        """
        Initialize the view as a terminal view.
        """
        self._cmd = cmd
        self._cwd = cwd
        self._keep_open = keep_open

        # Start the underlying shell
        self._shell = linux_pty.LinuxPty(self._cmd, self._cwd)
        self._shell_is_running = True

        # Initialize the sublime view
        self._terminal_buffer = \
            sublime_terminal_buffer.SublimeTerminalBuffer(self.view, title, syntax)
        self._terminal_buffer.set_keypress_callback(self.keypress_callback)
        self._terminal_buffer.set_write_process_input_callback(self.send_string_to_shell)
        self._terminal_buffer_is_open = True
        self._terminal_rows = 0
        self._terminal_columns = 0

        # Save the command args in view settings so it can restarted when ST3 is
        # restarted (or when changing back to a project that had a terminal view
        # open)
        args = {"cmd": cmd, "title": title, "cwd": cwd, "syntax": syntax, "keep_open": keep_open}
        self.view.settings().set("terminal_view_activate_args", args)

        # Register the terminal view instance in the manager
        TerminalViewManager.register(self.view.id(), self)

        # Start the main loop
        threading.Thread(target=self._main_update_loop).start()

    def keypress_callback(self, key, ctrl=False, alt=False, shift=False,
                          meta=False, app_mode=False):
        """
        Callback when a keypress is registered in the Sublime Terminal buffer.

        Args:
            key (str): String describing pressed key. May be a name like 'home'.
            ctrl (boolean, optional)
            alt (boolean, optional)
            shift (boolean, optional)
            meta (boolean, optional)
        """
        self._shell.send_keypress(key, ctrl, alt, shift, meta, app_mode)

    def send_string_to_shell(self, string):
        self._shell.send_string(string)

    def _main_update_loop(self):
        """
        This is the main update function. It attempts to run at a certain number
        of frames per second, and keeps input and output synchronized.
        """
        # 30 frames per second should be responsive enough
        ideal_delta = 1.0 / 30.0
        current = time.time()
        start_time = current
        while True:
            self._poll_shell_output()
            self._terminal_buffer.update_view()
            self._resize_screen_if_needed()
            if not self._shell.is_running():
                self._poll_shell_output()
                break

            if not self._terminal_buffer.is_open():
                break

            # We use hard sleep here instead of any fancy timeout on the polling
            # to avoid excessive amounts of updates. When you hit enter for
            # example, the shell sends 2 bytes first (\r\n) and then the new
            # prompt. We do not want to trigger two updates in this case as the
            # bottom line of terminal will appear to blink quickly.
            previous = current
            current = time.time()
            actual_delta = current - previous
            time_left = ideal_delta - actual_delta
            if time_left > 0.0:
                time.sleep(time_left)

        # Notify user that cmd has exitted
        run_time = time.time() - start_time
        self._show_close_message_in_terminal(run_time)
        self._stop()

    def _poll_shell_output(self, timeout=0):
        """
        Poll the output of the shell
        """
        max_read_size = 2**12
        data = self._shell.receive_output(max_read_size, timeout=timeout)
        if data is not None:
            utils.ConsoleLogger.log("Got %u bytes of data from shell" % (len(data), ))
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
            utils.ConsoleLogger.log(log)

            self._terminal_rows = rows
            self._terminal_columns = cols
            self._shell.update_screen_size(self._terminal_rows, self._terminal_columns)
            self._terminal_buffer.update_terminal_size(self._terminal_rows, self._terminal_columns)

    def _show_close_message_in_terminal(self, run_time):
        ret_code, signal = self._shell.exit_status()
        if signal > 0:
            close_reason = "terminated"
            close_msg = "by signal %i (%s)." % (signal, utils.unix_signal_name(signal))
        else:
            close_reason = "finished"
            close_msg = "with return code %i." % (ret_code, )

        msg = "\r\nTerminalView: Command %s after %.3f seconds " % (close_reason, run_time)
        msg += close_msg
        self._terminal_buffer.insert_data(msg.encode("utf-8"))

    def _stop(self):
        """
        Stop the terminal and close everything down.
        """
        self._terminal_buffer.deactivate()
        if not self._keep_open:
            self._terminal_buffer.close()
            self._terminal_buffer_is_open = False

        self._shell.stop()
        self._shell_is_running = False

        # When stopping deregister in the manager
        TerminalViewManager.deregister(self.view.id())

        # If view is kept open ensure it is not restarted
        self.view.settings().erase("terminal_view_activate_args")


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
        if TerminalViewManager.load_from_id(view.id()) is None:
            view.run_command("terminal_view_clear")
            args = settings.get("terminal_view_activate_args")
            view.run_command("terminal_view_activate", args=args)


class TerminalViewSendString(sublime_plugin.WindowCommand):
    """
    Command to send a string to an active terminal.

    Example to send sigint:
        window.run_command("terminal_view_send_string", args={"string": "\x03"})
    """
    def run(self, string, current_window_only=True):
        """
        Send a string

        Args:
            string (str): string of characters to send
            current_window_only (bool, optional): constrain terminal search to
                                                  the current ST window only
        """
        if current_window_only:
            windows = [self.window]
        else:
            windows = sublime.windows()

        term_view = None
        for w in windows:
            for v in w.views():
                term_view = TerminalViewManager.load_from_id(v.id())
                if term_view is not None:
                    group, index = w.get_view_index(v)
                    active_view = w.active_view_in_group(group)
                    if active_view == v:
                        break

        if term_view is None:
            utils.ConsoleLogger.log("No terminal found")
            return

        term_view.send_string_to_shell(string)
