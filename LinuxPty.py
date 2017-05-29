import os
import select
import subprocess
import struct
import sublime
if sublime.platform() in ("linux", "osx"):
    import fcntl
    import termios
elif sublime.platform() == "windows":
    pass
    # TODO

class LinuxPty(object):
    def __init__(self, *cmd):
        self._cmd = cmd
        self._env = os.environ.copy()
        self._env["TERM"] = "linux"
        (self._pty, self._pts) = os.openpty()
        self._process = subprocess.Popen(self._cmd, stdin=self._pts,
                                         stdout=self._pts, stderr=self._pts, shell=False,
                                         env=self._env, close_fds=True, preexec_fn=os.setsid)

    def stop(self):
        if self.is_running():
            self._process.kill()
        self._process = None
        return

    def receive_output(self, max_read_size):
        (r, w, x) = select.select([self._pty], [], [], 0)
        if not r:
            return None

        if not self.is_running():
            return None

        return os.read(self._pty, max_read_size)

    def update_screen_size(self, lines, columns):
        # Note, assume ws_xpixel and ws_ypixel are zero.
        TIOCSWINSZ = getattr(termios, 'TIOCSWINSZ', -2146929561)
        s = struct.pack('HHHH', lines, columns, 0, 0)
        fcntl.ioctl(self._pts, TIOCSWINSZ, s)

    def is_running(self):
        return self._process is not None and self._process.poll() is None

    def send_keypress(self, key, ctrl=False, alt=False, shift=False, super=False):
        # If control was pressed together with single key send the combination
        # to the shell
        if ctrl and len(key) is 1:
            self._send_control_key_combination(key)
            return

        key = convert_key_to_ansi(key)
        self._send_string(key)

    def _send_control_key_combination(self, key):
        # Convert to lower case and get unicode representation of char
        char = key.lower()
        a = ord(char)

        if a>=97 and a<=122:
            a = a - ord('a') + 1
            return self._send_string(chr(a))

        # Handle special chars
        d = {'@': 0, '`': 0, '[': 27, '{': 27, '\\': 28, '|': 28, ']': 29,
             '}': 29, '^': 30, '~': 30, '_': 31, '?': 127}

        if char in d:
            self._send_string(chr(d[char]))

        return None

    def _send_string(self, string):
        if self.is_running():
            os.write(self._pty, string.encode('UTF-8'))


_LINUX_KEY_MAP = {
    "enter": "\n",
    "backspace": "\b",
    "tab": "\t",
    "space": " ",
    "escape": "\x1b",
    "down": "\x1b[B",
    "up": "\x1b[A",
    "right": "\x1b[C",
    "left": "\x1b[D",
    "home": "\x1b[H",
    "end": "\x1b[F",
    "pageup": "\x1b[5~",
    "pagedown": "\x1b[6~",
    "delete": "\x1b[3~",
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

def convert_key_to_ansi(key):
    if key in _LINUX_KEY_MAP:
        return _LINUX_KEY_MAP[key]
    return key
