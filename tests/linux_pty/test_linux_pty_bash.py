"""
Unittests for the LinuxPty module when using bash as shell
"""
import os
import unittest
import time

# Module to test
from TerminalView import linux_pty


class BashTestBase(unittest.TestCase):
    """
    Some helper functions for bash testcases
    """
    def setUp(self):
        """
        Start bash shell
        """
        cwd = os.path.dirname(os.path.abspath(__file__))
        self.linux_pty_bash = linux_pty.LinuxPty("/bin/bash", cwd)
        self.assertTrue(self.linux_pty_bash.is_running())

        # Update screen size to avoid wrapping during test
        self.linux_pty_bash.update_screen_size(80, 500)

        # Read the initial prompt - note this has to be placed after resize
        self.linux_pty_bash.receive_output(1024, timeout=1)

    def tearDown(self):
        """
        Stop bash shell
        """
        self.assertTrue(self.linux_pty_bash.is_running())
        self.linux_pty_bash.stop()
        self.assertFalse(self.linux_pty_bash.is_running())

    def _reset_shell_output(self):
        self.linux_pty_bash.send_keypress("c", ctrl=True)
        self._read_bytes_from_shell(1024, timeout=0.5)
        self.linux_pty_bash.send_keypress("l", ctrl=True)
        self._read_bytes_from_shell(1024, timeout=0.5)

    def _prepare_verbatim_insert(self):
        """
        Prepare verbatim insert so the shell echoes the pressed key
        """
        self.linux_pty_bash.send_keypress("v", ctrl=True)
        time.sleep(0.5)

    def _read_bytes_from_shell(self, num_bytes, timeout=1):
        """
        Try to read X bytes from shell but timeout after Y seconds
        """
        data = b''
        start = time.time()
        while (len(data) < num_bytes) and (time.time() < start + timeout):
            new_data = self.linux_pty_bash.receive_output(2048, timeout=0.1)
            if new_data is not None:
                data = data + new_data

        return data


class BashIOTest(BashTestBase):
    """
    Bash IO testcase
    """
    def test_single_ascii_chars(self):
        """
        Ensure that the LinuxPty module can send all single chars, numbers,
        signs to bash and that they are received correctly
        """
        # Make a list of all single chars/numbers etc. from ascii value 33 to
        # 126
        input_list = [chr(a) for a in range(33, 127)]

        # Send each input to the shell
        for char in input_list:
            self.linux_pty_bash.send_keypress(char)
            data = self.linux_pty_bash.receive_output(1, timeout=1)
            self.assertEqual(len(data), 1)
            self.assertEqual(data.decode('ascii'), char)

    def test_special_keys(self):
        """
        Ensure special keys like home, end, space, enter, arrow keys, etc. are
        sent and handled corretly by the shell
        """
        # Tested in Linux term (TERM=linux) on Centos 7 the shell responded with
        # the following.
        keymap = {
            "enter": "^M",
            "backspace": "^?",
            "tab": "   ",
            "space": " ",
            "escape": "^[",
            "down": "^[[B",
            "up": "^[[A",
            "right": "^[[C",
            "left": "^[[D",
            "home": "^[[1~",
            "end": "^[[4~",
            "pageup": "^[[5~",
            "pagedown": "^[[6~",
            "delete": "^[[3~",
            "insert": "^[[2~",
        }

        # Send each input to the shell
        for key in keymap:
            # Use verbatim insert to see which keys are pressed
            self._prepare_verbatim_insert()

            # Send keypress
            self.linux_pty_bash.send_keypress(key)

            # Check response
            if key == "tab":
                expected_response = " "
                data = self._read_bytes_from_shell(64, timeout=1)
                data = data.decode('ascii')
                for char in data:
                    self.assertEqual(char, " ", msg="Non-space in tab")
            else:
                expected_response = keymap[key]
                data = self._read_bytes_from_shell(len(expected_response))
                self.assertEqual(len(data), len(expected_response), msg=data)
                self.assertEqual(data.decode('ascii'), expected_response, msg=data)

    def test_ctrl_key_combinations(self):
        """
        Ensure that the LinuxPty module can send all ctrl + char combinations to
        bash and that they are received correctly
        """
        # Make a list of all single chars from ascii value 97 to 122
        input_list = [chr(a) for a in range(97, 123)]

        # Send each input to the shell
        for char in input_list:
            # Use verbatim insert to see which keys are pressed
            self._prepare_verbatim_insert()

            # Send key
            self.linux_pty_bash.send_keypress(char, ctrl=True)

            # Read back result we expect ^A, ^B, ^C, etc. Note that the ctrl+i
            # and ctrl+j combination are ignored and translates differently
            if char == "i":
                data = self._read_bytes_from_shell(64, timeout=1)
                data = data.decode('ascii')
                # Ensure data is only spaces
                for character in data:
                    self.assertEqual(character, " ")
            elif char == "j":
                data = self._read_bytes_from_shell(3, timeout=5)
                self.assertEqual(len(data), 3)
                self.assertEqual(data.decode('ascii'), "\r\n\r")
            else:
                data = self._read_bytes_from_shell(2, timeout=5)
                self.assertEqual(len(data), 2)
                self.assertEqual(data.decode('ascii'), "^" + char.upper())

    def test_ctrl_key_sign_combinations(self):
        """
        Ensure that the LinuxPty module can send all ctrl + sign combinations to
        bash and that they are received correctly
        """
        # Make a list of signs to test (note that arrow keys are included)
        keymap = {
            "[": "^[",
            "\\": "^\\",
            "]": "^]",
            "^": "^^",
            "_": "^_",
            "?": "^?",
            "left": "^[[1;5D",
            "right": "^[[1;5C",
        }

        # Send each input to the shell
        for sign in keymap:
            # Use verbatim insert to see which keys are pressed
            self._prepare_verbatim_insert()

            # Send key
            self.linux_pty_bash.send_keypress(sign, ctrl=True)

            # Read back result we expect ^[, ^\, ^], etc.
            expected_response = keymap[sign]
            data = self._read_bytes_from_shell(len(expected_response), timeout=5)
            self.assertEqual(len(data), len(expected_response), msg=data)
            self.assertEqual(data.decode('ascii'), expected_response, msg=data)

    def test_alt_key_combinations(self):
        """
        Ensure that the LinuxPty module can send all alt + char combinations to
        bash and that they are received correctly
        """
        # Make a list of all single chars from ascii value 97 to 122
        input_list = [chr(a) for a in range(97, 123)]

        # Send each input to the shell
        for char in input_list:
            # Use verbatim insert to see which keys are pressed
            self._prepare_verbatim_insert()

            # Send key
            self.linux_pty_bash.send_keypress(char, alt=True)

            # Read back result we expect ^[a, ^[b, ^[c, etc.
            data = self._read_bytes_from_shell(3, timeout=5)
            fail_msg = "Char: [%s], Data: [%s]" % (char, data.decode('ascii'))
            self.assertEqual(len(data), 3, msg=fail_msg)
            self.assertEqual(data.decode('ascii'), "^[" + char, msg=fail_msg)


class BashResizeTest(BashTestBase):
    """
    Bash scren resize testcase
    """
    def test_tput_output(self):
        """
        Ensure tput reports the correct screen sizes when executed in the bash
        shell
        """
        screen_sizes = [(80, 500), (800, 45), (30, 250)]

        # Get the screen size that tput reads when run in the shell
        cols_cmd = "tput cols"
        lines_cmd = "tput lines"
        for size in screen_sizes:
            # Resize the screen and reset
            self.linux_pty_bash.update_screen_size(size[0], size[1])
            self._reset_shell_output()

            # Send cols cmd
            for char in cols_cmd:
                self.linux_pty_bash.send_keypress(char)
            self.linux_pty_bash.send_keypress("enter")

            # Read output of the cmd
            data = self._read_bytes_from_shell(512, timeout=0.5)
            cols = data.decode('ascii').split("\r\n")[1]
            self.assertEqual(int(cols), size[1])

            # Send lines cmd
            for char in lines_cmd:
                self.linux_pty_bash.send_keypress(char)
            self.linux_pty_bash.send_keypress("enter")

            # Read output of the cmd
            data = self._read_bytes_from_shell(512, timeout=0.5)
            lines = data.decode('ascii').split("\r\n")[1]
            self.assertEqual(int(lines), size[0])
