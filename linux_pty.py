"""
Wrapper module around a Linux PTY which can be used to start an underlying shell
"""

import os
import select
import struct
import time
import pty
import signal

try:
    import fcntl
    import termios
except ImportError:
    pass

from . import utils


class LinuxPty():
    """
    Linux PTY class that starts an underlying shell and provides methods for
    communicating with it
    """
    def __init__(self, cmd, cwd):
        self._shell_pid, self._master_fd = pty.fork()
        if self._shell_pid == pty.CHILD:
            os.environ["TERM"] = "linux"
            os.chdir(cwd)
            os.execv(cmd[0], cmd)

    def __del__(self):
        utils.ConsoleLogger.log("Linux PTY instance deleted")

    def stop(self):
        """
        Stop the shell
        """
        if self.is_running():
            try:
                os.kill(self._shell_pid, signal.SIGTERM)
            except OSError:
                pass

        start = time.time()
        while self.is_running() and (time.time() < (start + 0.2)):
            time.sleep(0.05)

        if self.is_running():
            utils.ConsoleLogger.log("Failed to stop shell process")
        else:
            utils.ConsoleLogger.log("Shell process stopped")

    def receive_output(self, max_read_size, timeout=0):
        """
        Poll the shell output
        """
        (ready, _, _) = select.select([self._master_fd], [], [], timeout)
        if not ready:
            return None

        try:
            data = os.read(self._master_fd, max_read_size)
        except OSError:
            return None

        return data

    def update_screen_size(self, lines, columns):
        """
        Notify the shell of a terminal screen resize
        """
        if self.is_running:
            # Note, assume ws_xpixel and ws_ypixel are zero.
            tiocswinsz = getattr(termios, 'TIOCSWINSZ', -2146929561)
            size_update = struct.pack('HHHH', lines, columns, 0, 0)
            fcntl.ioctl(self._master_fd, tiocswinsz, size_update)

    def is_running(self):
        """
        Check if the shell is running
        """
        try:
            pid, status = os.waitpid(self._shell_pid, os.WNOHANG)
        except OSError:
            return False
        return True

    def send_keypress(self, key, ctrl=False, alt=False, shift=False, meta=False,
                      app_mode=False):
        """
        Send keypress to the shell
        """
        if ctrl:
            keycode = self._get_ctrl_combination_key_code(key)
        elif alt:
            keycode = self._get_alt_combination_key_code(key)
        else:
            if app_mode:
                keycode = self._get_app_key_code(key)
            else:
                keycode = self._get_key_code(key)

        self.send_string(keycode)

    def send_string(self, string):
        if self.is_running():
            os.write(self._master_fd, string.encode('UTF-8'))

    def _get_ctrl_combination_key_code(self, key):
        key = key.lower()
        if key in _LINUX_CTRL_KEY_MAP:
            return _LINUX_CTRL_KEY_MAP[key]
        elif len(key) == 1:
            unicode = ord(key)
            if (unicode >= 97) and (unicode <= 122):
                unicode = unicode - ord('a') + 1
                return chr(unicode)
            return self._get_key_code(key)

        return self._get_key_code(key)

    def _get_alt_combination_key_code(self, key):
        key = key.lower()
        if key in _LINUX_ALT_KEY_MAP:
            return _LINUX_ALT_KEY_MAP[key]

        code = self._get_key_code(key)
        return "\x1b" + code

    def _get_app_key_code(self, key):
        if key in _LINUX_APP_KEY_MAP:
            return _LINUX_APP_KEY_MAP[key]
        return self._get_key_code(key)

    def _get_key_code(self, key):
        if key in _LINUX_KEY_MAP:
            return _LINUX_KEY_MAP[key]
        return key


_LINUX_KEY_MAP = {
    "enter": "\r",
    "backspace": "\x7f",
    "tab": "\t",
    "space": " ",
    "escape": "\x1b",
    "down": "\x1b[B",
    "up": "\x1b[A",
    "right": "\x1b[C",
    "left": "\x1b[D",
    "home": "\x1b[1~",
    "end": "\x1b[4~",
    "pageup": "\x1b[5~",
    "pagedown": "\x1b[6~",
    "delete": "\x1b[3~",
    "insert": "\x1b[2~",
    "f1": "\x1bOP",
    "f2": "\x1bOQ",
    "f3": "\x1bOR",
    "f4": "\x1bOS",
    "f5": "\x1b[15~",
    "f6": "\x1b[17~",
    "f7": "\x1b[18~",
    "f8": "\x1b[19~",
    "f9": "\x1b[20~",
    "f10": "\x1b[21~",
    "f12": "\x1b[24~",
    "bracketed_paste_mode_start": "\x1b[200~",
    "bracketed_paste_mode_end": "\x1b[201~",
}

_LINUX_APP_KEY_MAP = {
    "down": "\x1bOB",
    "up": "\x1bOA",
    "right": "\x1bOC",
    "left": "\x1bOD",
}

_LINUX_CTRL_KEY_MAP = {
    "up": "\x1b[1;5A",
    "down": "\x1b[1;5B",
    "right": "\x1b[1;5C",
    "left": "\x1b[1;5D",
    "@": "\x00",
    "`": "\x00",
    "[": "\x1b",
    "{": "\x1b",
    "\\": "\x1c",
    "|": "\x1c",
    "]": "\x1d",
    "}": "\x1d",
    "^": "\x1e",
    "~": "\x1e",
    "_": "\x1f",
    "?": "\x7f",
}

_LINUX_ALT_KEY_MAP = {
    "up": "\x1b[1;3A",
    "down": "\x1b[1;3B",
    "right": "\x1b[1;3C",
    "left": "\x1b[1;3D",
}
