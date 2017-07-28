"""
Main module for the TerminalView plugin with commands for opening and
initializing a terminal view
"""

import os
import sublime
import sublime_plugin


class TerminalViewOpen(sublime_plugin.WindowCommand):
    """
    Main entry command for opening a terminal view. Only one instance of this
    class per sublime window. Once a terminal view has been opened the
    TerminalViewActivate instance for that view is called to handle everything.
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
            syntax (str, optional): Syntax file to use in the view.
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

        # args = {"cmd": cmd, "title": title, "cwd": cwd, "syntax": syntax}
        # self.window.new_file().run_command("terminal_view_activate", args=args)
        view = self.window.new_file()
        view.set_name(title)
        if syntax:
            view.set_syntax_file("Packages/User/" + syntax)
        view.settings().set("_terminal_view_cmd", cmd)
        view.settings().set("_terminal_view_cwd", cwd)
        view.settings().set("gutter", False)
        view.settings().set("highlight_line", False)
        view.settings().set("auto_complete_commit_on_tab", False)
        view.settings().set("draw_centered", False)
        view.settings().set("word_wrap", False)
        view.settings().set("auto_complete", False)
        view.settings().set("draw_white_space", "none")
        view.settings().set("draw_indent_guides", False)
        view.settings().set("caret_style", "blink")
        view.settings().set("scroll_past_end", False)
        view.settings().add_on_change(
            "color_scheme",
            lambda: set_color_scheme(view))
        view.set_scratch(True)
        view.set_read_only(True)
        view.settings().set("_terminal_view", True)


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
