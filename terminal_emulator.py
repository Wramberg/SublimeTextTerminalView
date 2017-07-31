"""
Wrapper module for the Pyte terminal emulator
"""
from collections import deque, namedtuple
from itertools import islice
import math

from . import pyte
from .pyte import modes


class PyteTerminalEmulator():
    """
    Adapter for the pyte terminal emulator
    """
    def __init__(self, cols, lines, history, ratio):
        # Double history size due to pyte splitting it between two queues
        # resulting in only having half the scrollback as expected
        self._screen = CustomHistoryScreen(cols, lines, history * 2, ratio)
        self._bytestream = pyte.ByteStream()
        self._bytestream.attach(self._screen)

    def feed(self, data):
        self._screen.scroll_to_bottom()
        self._bytestream.feed(data)

    def resize(self, lines, cols):
        self._screen.scroll_to_bottom()
        dirty_lines = max(lines, self._screen.lines)
        self._screen.dirty.update(range(dirty_lines))
        return self._screen.resize(lines, cols)

    def prev_page(self):
        self._screen.prev_page()

    def next_page(self):
        self._screen.next_page()

    def dirty_lines(self):
        dirty_lines = {}
        nb_dirty_lines = len(self._screen.dirty)
        if nb_dirty_lines > 0:
            display = self._screen.display
            for line in self._screen.dirty:
                if line >= len(display):
                    # This happens when screen is resized smaller
                    dirty_lines[line] = None
                else:
                    dirty_lines[line] = display[line]

        return dirty_lines

    def clear_dirty(self):
        return self._screen.dirty.clear()

    def cursor(self):
        cursor = self._screen.cursor
        if cursor:
            return (cursor.y, cursor.x)

        return (0, 0)

    def color_map(self, lines):
        return convert_pyte_buffer_to_colormap(self._screen.buffer, lines)

    def display(self):
        return self._screen.display

    def bracketed_paste_mode_enabled(self):
        return (2004 << 5) in self._screen.mode


History = namedtuple("History", "top bottom ratio size position")
Margins = namedtuple("Margins", "top bottom")


class CustomHistoryScreen(pyte.HistoryScreen):

    def scroll_to_bottom(self):
        """
        Ensure a screen is at the bottom of the history buffer
        """
        while self.history.position < self.history.size:
            self.next_page()


def take(n, iterable):
    """Returns first n items of the iterable as a list."""
    return list(islice(iterable, n))


def convert_pyte_buffer_to_colormap(buffer, lines):
    """
    Convert a pyte buffer to a simple colors
    """
    color_map = {}
    for line_index in lines:
        # There may be lines outside the buffer after terminal was resized.
        # These are considered blank.
        if line_index > len(buffer) - 1:
            break

        # Get line and process all colors on that. If there are multiple
        # continuous fields with same color we want to combine them for
        # optimization and because it looks better when rendered in ST3.
        line = buffer[line_index]
        line_len = len(line)
        if line_len == 0:
            continue

        # Initialize vars to keep track of continuous colors
        last_bg = line[0].bg
        if last_bg == "default":
            last_bg = "black"

        last_fg = line[0].fg
        if last_fg == "default":
            last_fg = "white"

        if line[0].reverse:
            last_color = (last_fg, last_bg)
        else:
            last_color = (last_bg, last_fg)

        last_index = 0
        field_length = 0

        char_index = 0
        for char in line.values():
            # Default bg is black
            if char.bg is "default":
                bg = "black"
            else:
                bg = char.bg

            # Default fg is white
            if char.fg is "default":
                fg = "white"
            else:
                fg = char.fg

            if char.reverse:
                color = (fg, bg)
            else:
                color = (bg, fg)

            if last_color == color:
                field_length = field_length + 1
            else:
                color_dict = {"color": last_color, "field_length": field_length}

                if last_color != ("black", "white"):
                    if line_index not in color_map:
                        color_map[line_index] = {}
                    color_map[line_index][last_index] = color_dict

                last_color = color
                last_index = char_index
                field_length = 1

            # Check if last color was active to the end of screen
            if last_color != ("black", "white"):
                color_dict = {"color": last_color, "field_length": field_length}
                if line_index not in color_map:
                    color_map[line_index] = {}
                color_map[line_index][last_index] = color_dict

            char_index = char_index + 1
    return color_map
