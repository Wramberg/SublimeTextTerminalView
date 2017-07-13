"""
Wrapper module around a Linux PTY which can be used to start an underlying shell
"""

import os
import select
import subprocess
import struct
import signal

try:
    import fcntl
    import termios
    import tty
except ImportError:
    pass


class LinuxPty():
    """
    Linux PTY class that starts an underlying and provides methods for
    communicating with it
    """
    def __init__(self, cmd, cwd):
        self._cmd = cmd
        self._env = os.environ.copy()
        self._env["TERM"] = "linux"
        (self._pty, self._pts) = os.openpty()
        self._process = subprocess.Popen(self._cmd, stdin=self._pts,
                                         stdout=self._pts, stderr=self._pts, shell=False,
                                         env=self._env, close_fds=True, start_new_session=True,
                                         cwd=cwd)

    def stop(self):
        """
        Stop the shell
        """
        if self.is_running():
            self._process.kill()
        self._process = None
        return

    def receive_output(self, max_read_size, timeout=0):
        """
        Poll the shell output
        """
        if not self.is_running():
            return None

        (ready, _, _) = select.select([self._pty], [], [], timeout)
        if not ready:
            return None

        return os.read(self._pty, max_read_size)

    def update_screen_size(self, lines, columns):
        """
        Notify the shell of a terminal screen resize
        """
        if self.is_running:
            # Note, assume ws_xpixel and ws_ypixel are zero.
            tiocswinsz = getattr(termios, 'TIOCSWINSZ', -2146929561)
            size_update = struct.pack('HHHH', lines, columns, 0, 0)
            fcntl.ioctl(self._pts, tiocswinsz, size_update)
            if not self.is_ignoring_signal():
                self._send_signal("SIGWINCH")

    def is_running(self):
        """
        Check if the shell is running
        """
        return self._process is not None and self._process.poll() is None

    def is_ignoring_signal(self):
        """
        Check if the pty is ignoring signal
        """
        attr = termios.tcgetattr(self._pts)
        return attr[tty.LFLAG] & termios.ISIG == 0

    def send_keypress(self, key, ctrl=False, alt=False, shift=False, meta=False):
        """
        Send keypress to the shell
        """

        # check if the keypress will translate into signal
        if not self.is_ignoring_signal():
            if ctrl:
                sig = self._get_ctrl_signal_code(key)
                if sig:
                    self._send_signal(sig)
                    return

        if ctrl:
            keycode = self._get_ctrl_combination_key_code(key)
        elif alt:
            keycode = self._get_alt_combination_key_code(key)
        else:
            keycode = self._get_key_code(key)

        self._send_string(keycode)

    def _send_signal(self, s):
        if self.is_running:
            if s in dir(signal):
                signum = getattr(signal, s)
                os.killpg(self._process.pid, signum)

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

    def _get_key_code(self, key):
        if key in _LINUX_KEY_MAP:
            return _LINUX_KEY_MAP[key]

        return key

    def _get_ctrl_signal_code(self, key):
        if key in _LINUX_CTRL_SIGNAL_MAP:
            return _LINUX_CTRL_SIGNAL_MAP[key]

        return None

    def _send_string(self, string):
        if self.is_running():
            os.write(self._pty, string.encode('UTF-8'))


_LINUX_CTRL_SIGNAL_MAP = {
    "c": "SIGINT",
    "z": "SIGTSTP",
    "\\": "SIGQUIT"
}


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
