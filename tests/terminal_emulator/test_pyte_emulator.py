import unittest

from TerminalView import pyte_terminal_emulator

class terminal_resize(unittest.TestCase):
    def test_lines_resize(self):
        nb_cols = 20
        nb_lines = 6
        emulator = pyte_terminal_emulator.PyteTerminalEmulator(cols=nb_cols, lines=nb_lines,
                                                               history=100, ratio=10.5)
        lines = []
        lines.append("line 1")
        lines.append("line TWO")
        lines.append("line number three")

        for line in lines:
            emulator.feed((line + "\r\n").encode("utf8"))

        display = emulator.display()
        self.assertEqual(len(display), nb_lines)
        for i in range(len(lines)):
            self.assertEqual(display[i], lines[i].ljust(nb_cols))

        # Remove two lines - we expect bottom ones to be removed since they are
        # blank
        nb_lines = 4
        emulator.resize(nb_lines, nb_cols)
        display = emulator.display()
        self.assertEqual(len(display), nb_lines)
        for i in range(len(lines)):
            self.assertEqual(display[i], lines[i].ljust(nb_cols))

        # Remove another line
        nb_lines = 3
        emulator.resize(nb_lines, nb_cols)
        display = emulator.display()
        self.assertEqual(len(display), nb_lines)
        for i in range(len(lines)):
            self.assertEqual(display[i], lines[i].ljust(nb_cols))

        # Remove another - now we expect the top line to be removed
        nb_lines = 2
        emulator.resize(nb_lines, nb_cols)
        display = emulator.display()
        self.assertEqual(len(display), nb_lines)
        for i in range(len(display)):
            self.assertEqual(display[i], lines[i+1].ljust(nb_cols))


class pyte_buffer_to_color_map(unittest.TestCase):
    def test_no_colors(self):
        buffer_factory = PyteBufferStubFactory(14, 37)
        pyte_buffer = buffer_factory.produce()
        lines = list(range(14))
        color_map = pyte_terminal_emulator.convert_pyte_buffer_to_colormap(pyte_buffer, lines)
        self.assertDictEqual(color_map, {})

    def test_lines_selection(self):
        lines = [2, 3, 6, 19]
        colors = ["red", "green", "magenta", "blue", "cyan"]
        buffer_factory = PyteBufferStubFactory(20, 10)
        for i in range(20):
            buffer_factory.set_color(i, 5, colors[i % len(colors)], "default")

        pyte_buffer = buffer_factory.produce()
        color_map = pyte_terminal_emulator.convert_pyte_buffer_to_colormap(pyte_buffer, lines)

        expected = {
            2: {
                5: {'color': ('magenta', 'white'), 'field_length': 1}
            },
            3: {
                5: {'color': ('blue', 'white'), 'field_length': 1}
            },
            6: {
                5: {'color': ('green', 'white'), 'field_length': 1}
            },
            19: {
                5: {'color': ('cyan', 'white'), 'field_length': 1}
            }
        }

        self.assertDictEqual(color_map, expected)

    def test_field_length1(self):
        buffer_factory = PyteBufferStubFactory(25, 20)

        buffer_factory.set_color(3, 11, "red", "green")
        buffer_factory.set_color(3, 12, "red", "green")
        buffer_factory.set_color(3, 13, "red", "green")

        buffer_factory.set_color(8, 1, "blue", "yellow")
        buffer_factory.set_color(8, 2, "blue", "yellow")
        buffer_factory.set_color(8, 3, "blue", "yellow")
        buffer_factory.set_color(8, 4, "blue", "yellow")
        buffer_factory.set_color(8, 5, "blue", "yellow")
        buffer_factory.set_color(8, 6, "blue", "yellow")

        buffer_factory.set_color(8, 8, "blue", "yellow")

        buffer_factory.set_color(24, 1, "yellow", "yellow")
        buffer_factory.set_color(24, 17, "yellow", "yellow")
        buffer_factory.set_color(24, 18, "yellow", "yellow")
        buffer_factory.set_color(24, 19, "yellow", "yellow")

        buffer_factory.set_color(0, 0, "yellow", "cyan")
        buffer_factory.set_color(0, 1, "yellow", "cyan")
        buffer_factory.set_color(0, 2, "yellow", "cyan")
        buffer_factory.set_color(0, 3, "red", "cyan")

        pyte_buffer = buffer_factory.produce()
        lines = list(range(25))
        color_map = pyte_terminal_emulator.convert_pyte_buffer_to_colormap(pyte_buffer, lines)

        expected = {
            0: {
                0: {'color': ('yellow', 'cyan'), 'field_length': 3},
                3: {'color': ('red', 'cyan'), 'field_length': 1}
            },
            8: {
                8: {'color': ('blue', 'yellow'), 'field_length': 1},
                1: {'color': ('blue', 'yellow'), 'field_length': 6}
            },
            3: {
                11: {'color': ('red', 'green'), 'field_length': 3}
            },
            24: {
                1: {'color': ('yellow', 'yellow'), 'field_length': 1},
                17: {'color': ('yellow', 'yellow'), 'field_length': 3}
            }
        }

        self.assertDictEqual(color_map, expected)

    def test_field_length2(self):
        buffer_factory = PyteBufferStubFactory(4, 9)

        buffer_factory.set_color(3, 4, "red", "green")
        buffer_factory.set_color(3, 5, "red", "green")
        buffer_factory.set_color(3, 6, "red", "green")

        buffer_factory.set_color(0, 3, "yellow", "cyan")
        buffer_factory.set_color(0, 4, "yellow", "cyan")

        pyte_buffer = buffer_factory.produce()
        lines = list(range(4))
        color_map = pyte_terminal_emulator.convert_pyte_buffer_to_colormap(pyte_buffer, lines)

        expected = {
            3: {
                4: {
                    'color': ('red', 'green'),
                    'field_length': 3
                },
            },
            0: {
                3: {
                    'color': ('yellow', 'cyan'),
                    'field_length': 2
                }
            },
        }

        self.assertDictEqual(color_map, expected)

    def test_reverse_default_colors(self):
        buffer_factory = PyteBufferStubFactory(1, 13)
        buffer_factory.set_color(0, 0, "default", "default", True)
        buffer_factory.set_color(0, 1, "default", "default", True)
        buffer_factory.set_color(0, 2, "default", "default", True)

        buffer_factory.set_color(0, 3, "red", "default", True)
        buffer_factory.set_color(0, 4, "red", "default", True)
        buffer_factory.set_color(0, 5, "red", "default", True)

        buffer_factory.set_color(0, 6, "green", "default", True)
        buffer_factory.set_color(0, 7, "green", "default", True)
        buffer_factory.set_color(0, 8, "green", "default", True)

        buffer_factory.set_color(0, 9, "cyan", "default", True)
        buffer_factory.set_color(0, 10, "cyan", "default", True)
        buffer_factory.set_color(0, 11, "cyan", "default", True)

        pyte_buffer = buffer_factory.produce()
        color_map = pyte_terminal_emulator.convert_pyte_buffer_to_colormap(pyte_buffer, [0])

        expected = {
            0: {
                0: {
                    'field_length': 3,
                    'color': ('white', 'black')
                },
                9: {
                    'field_length': 3,
                    'color': ('white', 'cyan')
                },
                3: {
                    'field_length': 3,
                    'color': ('white', 'red')
                },
                6: {
                    'field_length': 3,
                    'color': ('white', 'green')
                }
            }
        }

        self.assertDictEqual(color_map, expected)


class PyteBufferStubFactory():
    def __init__(self, nb_lines, nb_cols):
        default_char = CharStub("default", "default", reverse=False)

        self.buffer = []
        for i in range(nb_lines):
            line = []
            for j in range(nb_cols):
                # line[j] = default_char # in newer version of pyte line is a dict
                line.append(default_char)
            self.buffer.append(line)

    def set_color(self, line, col, bg, fg, reverse=False):
        self.buffer[line][col] = CharStub(bg, fg, reverse=reverse)

    def produce(self):
        return self.buffer


class CharStub():
    def __init__(self, bg, fg, reverse=False):
        self.bg = bg
        self.fg = fg
        self.reverse = reverse
