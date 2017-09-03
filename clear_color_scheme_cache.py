"""Removes all trace of generated color schemes."""
import sublime
import sublime_plugin
import shutil
import os


class TerminalViewClearColorSchemeCacheCommand(sublime_plugin.ApplicationCommand):
    """Removes the folder $cache/User/TerminalView and $packages/User/TerminalView."""

    def run(self):
        """Run this command."""
        self._force_remove(os.path.join(sublime.cache_path(), "User", "TerminalView"))
        self._force_remove(os.path.join(sublime.packages_path(), "User", "TerminalView"))
        sublime.message_dialog("Cache is cleared.")

    def _force_remove(self, path):
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass
