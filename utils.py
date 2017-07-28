"""
Some utility functions for the TerminalView plugin
"""
import time
import sublime
import sublime_plugin
from .TerminalView2 import TerminalView2

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


class TerminalViewSendString(sublime_plugin.WindowCommand):
    """
    A command to send any text to the active terminal.
    Example to send sigint:
        window.run_command("terminal_view_send_string", args={"string": "\x03"})
    """
    def run(self, string, current_window_only=True):
        inst = TerminalView2.active_instance()
        if inst:
            inst._shell.send_string(string)
