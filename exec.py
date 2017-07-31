import os
import sublime_plugin


class TerminalViewExec(sublime_plugin.WindowCommand):

    def run(self, *args, **kwargs):
        name = kwargs.get("name", "Executable")
        env = kwargs.get("env", {})
        env = os.environ.copy().update(env)
        cmd = kwargs.get("cmd", [])
        if not cmd:
            cmd = [kwargs.get("shell_cmd", "")]
        working_dir = kwargs.get("working_dir")
        if not working_dir:
            view = self.window.active_view()
            if view and view.file_name():
                working_dir = os.path.basedir(view.file_name())
            else:
                working_dir = env.get("HOME", "")
                if not working_dir:
                    working_dir = "/"
        args = kwargs.get("args", "")
        invocation = " ".join(cmd) + args
        self.window.run_command("terminal_view_open", args={
                                    "cmd": invocation,
                                    "cwd": working_dir,
                                    "title": name,
                                    "autoclose": False})
