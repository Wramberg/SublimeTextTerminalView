"""
Some utility functions for the TerminalView plugin
"""
import time
import sublime
import sublime_plugin


class ConsoleLogger():
    """
    Logger service
    """
    def __init__(self):
        settings = sublime.load_settings('TerminalView.sublime-settings')
        self._enabled = settings.get("terminal_view_print_debug", False)

    def log(self, string):
        """
        Log string to sublime text console if debug is enabled
        """
        if self._enabled:
            prefix = "[terminal_view debug] [%.3f] " % (time.time())
            print(prefix + string)


class TerminalViewManager():
    """
    A manager to control all TerminalView instance.
    """
    @classmethod
    def register(cls, terminal_view):
        if not hasattr(cls, "terminal_views"):
            cls.terminal_views = {}
        cls.terminal_views[terminal_view.view.id()] = terminal_view
        return terminal_view

    @classmethod
    def load_from_id(cls, vid):
        if vid in cls.terminal_views:
            return cls.terminal_views[vid]
        else:
            raise Exception("terminal view not found.")


class TerminalViewSendString(sublime_plugin.WindowCommand):
    """
    A command to send any text to the active terminal.
    Example to send sigint:
        window.run_command("terminal_view_send_string", args={"string": "\x03"})
    """
    def run(self, string, current_window_only=True):
        if current_window_only:
            windows = [self.window]
        else:
            windows = sublime.windows()
        view = None
        for w in windows:
            for v in w.views():
                if v.settings().get("terminal_view"):
                    group, index = w.get_view_index(v)
                    active_view = w.active_view_in_group(group)
                    if active_view == v:
                        view = v
                        break

        if not view:
            print("no terminal found.")
            return

        terminal_view = TerminalViewManager.load_from_id(view.id())
        terminal_view._shell._send_string(string)
