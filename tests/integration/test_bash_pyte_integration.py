import unittest
import os
import time
import socket
import getpass
import copy

from TerminalView import pyte_terminal_emulator
from TerminalView import linux_pty


class NanoSuspendResumeTest(unittest.TestCase):
    def test_suspend_resume(self):
        """
        Test that nano can be suspended and resumed. Pyte has had trouble with
        this so this test is here to ensure that the bug does not re-appear.
        """
        # Get some environment vars
        self.home_dir = os.environ["HOME"]
        self.hostname = socket.gethostname()
        self.username = getpass.getuser()
        self.shell_prompt = self.username + "@" + self.hostname + ":~$"

        # Expected display contents
        self.lines = 20
        self.columns = 80
        self.expected_display = []
        for i in range(self.lines):
            self.expected_display.append(" " * self.columns)

        # Expect prompt (do not handle line wrapping)
        self.expected_display[0] = self.shell_prompt.ljust(self.columns)
        self.cleared_display = copy.copy(self.expected_display)

        # Start terminal emulator
        self.term_emulator = pyte_terminal_emulator.PyteTerminalEmulator(10, 10, 1000, 0.5)

        # Start the shell
        self.linux_pty_bash = linux_pty.LinuxPty("/bin/bash", self.home_dir)
        self.assertTrue(self.linux_pty_bash.is_running())

        # Update screen size
        self.term_emulator.resize(self.lines, self.columns)
        self.linux_pty_bash.update_screen_size(self.lines, self.columns)

        # Read the initial prompt - note this has to be placed after resize
        data = self._read_bytes_from_shell(1024, timeout=1)
        self.term_emulator.feed(data)

        # Check display matches expected
        disp = self.term_emulator.display()
        for i in range(len(disp)):
            self.assertEqual(disp[i], self.expected_display[i])

        # Check current dir
        cmd = "pwd"
        for char in cmd:
            self.linux_pty_bash.send_keypress(char)
        self.linux_pty_bash.send_keypress("enter")

        # Update expected display
        first_line = self.shell_prompt + " pwd"
        self.expected_display[0] = first_line.ljust(self.columns)
        second_line = self.home_dir
        self.expected_display[1] = second_line.ljust(self.columns)
        self.expected_display[2] = self.shell_prompt.ljust(self.columns)

        # Read data
        data = self._read_bytes_from_shell(1024, timeout=1)
        self.term_emulator.feed(data)

        # Check display matches expected
        disp = self.term_emulator.display()
        for i in range(len(disp)):
            self.assertEqual(disp[i], self.expected_display[i])

        # Clear display
        self.linux_pty_bash.send_keypress("l", ctrl=True)
        self.expected_display = copy.copy(self.cleared_display)
        data = self._read_bytes_from_shell(1024, timeout=1)
        self.term_emulator.feed(data)

        # Check display matches expected
        disp = self.term_emulator.display()
        for i in range(len(disp)):
            self.assertEqual(disp[i], self.expected_display[i])

        # Open file in nano
        cmd = "nano test%.0f" % time.time()
        for char in cmd:
            self.linux_pty_bash.send_keypress(char)
        self.linux_pty_bash.send_keypress("enter")
        data = self._read_bytes_from_shell(1024, timeout=1)
        self.term_emulator.feed(data)

        # Wrikte a bit in the file and see that it works
        self.linux_pty_bash.send_keypress("a")
        self.linux_pty_bash.send_keypress("b")
        self.linux_pty_bash.send_keypress("c")
        data = self._read_bytes_from_shell(1024, timeout=1)
        self.term_emulator.feed(data)
        disp = self.term_emulator.display()
        self.expected_display = copy.copy(disp)

        # Suspend nano
        self.linux_pty_bash.send_keypress("z", ctrl=True)
        data = self._read_bytes_from_shell(4096, timeout=1)
        self.term_emulator.feed(data)
        disp = self.term_emulator.display()
        self.assertTrue(disp[-2].startswith("[1]+  Stopped"), msg=disp)
        self.assertEqual(disp[-1], self.shell_prompt.ljust(self.columns), msg=disp)

        # Bring nano back
        cmd = "fg"
        for char in cmd:
            self.linux_pty_bash.send_keypress(char)
        self.linux_pty_bash.send_keypress("enter")

        data = self._read_bytes_from_shell(4096, timeout=1)
        self.term_emulator.feed(data)

        # Check display matches expected
        disp = self.term_emulator.display()
        msg = {"expected": self.expected_display, "actual": disp}
        for i in range(len(disp)):
            # The new file line might be removed with resuming nano
            if "New File" not in self.expected_display[i]:
                self.assertEqual(disp[i], self.expected_display[i], msg=msg)

    def _read_bytes_from_shell(self, num_bytes, timeout=1):
        """
        Try to read X bytes from shell but timeout after Y seconds
        """
        data = b''
        start = time.time()
        while (len(data) < num_bytes) and (time.time() < start + timeout):
            new_data = self.linux_pty_bash.receive_output(2048)
            if new_data is not None:
                data = data + new_data

        return data
