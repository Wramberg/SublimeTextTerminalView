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
        self._modified = True

    def feed(self, data):
        self._screen.scroll_to_bottom()
        self._bytestream.feed(data)
        self._modified = True

    def resize(self, lines, cols):
        self._screen.scroll_to_bottom()
        dirty_lines = max(lines, self._screen.lines)
        self._screen.dirty.update(range(dirty_lines))
        self._modified = True
        return self._screen.resize(lines, cols)

    def prev_page(self):
        self._screen.prev_page()
        self._screen.ensure_screen_width()
        self._modified = True

    def next_page(self):
        self._screen.next_page()
        self._modified = True

    def dirty_lines(self):
        dirty_lines = {}
        nb_dirty_lines = len(self._screen.dirty)
        if nb_dirty_lines > 0:
            display = self._screen.display
            for line in self._screen.dirty:
                if line >= len(display):
                    # This happens when screen is resized smaller
                    break
                else:
                    dirty_lines[line] = display[line]

        return dirty_lines

    def clear_dirty(self):
        self._modified = False
        return self._screen.dirty.clear()

    def cursor(self):
        cursor = self._screen.cursor
        if cursor:
            return (cursor.y, cursor.x)

        return (0, 0)

    def cursor_is_hidden(self):
        if self._screen.cursor:
            return self._screen.cursor.hidden

        return False

    def color_map(self, lines):
        return convert_pyte_buffer_to_colormap(self._screen.buffer, lines)

    def display(self):
        return self._screen.display

    def modified(self):
        return self._modified

    def bracketed_paste_mode_enabled(self):
        return (2004 << 5) in self._screen.mode

    def application_mode_enabled(self):
        return False

    def nb_lines(self):
        return self._screen.lines

History = namedtuple("History", "top bottom ratio size position")
Margins = namedtuple("Margins", "top bottom")


class CustomHistoryScreen(pyte.DiffScreen):
    """
    Custom history screen customized for this plugin. Basically a copy of the
    standard pyte history screen but with some optimizations.
    """
    def __init__(self, columns, lines, history, ratio):
        self.history = History(deque(maxlen=history // 2),
                               deque(maxlen=history),
                               float(ratio),
                               history,
                               history)

        super(CustomHistoryScreen, self).__init__(columns, lines)

        # We do not agree with pyte about default tabstops
        self.tabstops = set(range(8, self.columns, 8))

    def reset(self):
        super(CustomHistoryScreen, self).reset()

        # Reset tab stops
        self.tabstops = set(range(8, self.columns, 8))

    def scroll_to_bottom(self):
        """
        Ensure a screen is at the bottom of the history buffer
        """
        while self.history.position < self.history.size:
            self.next_page()

    def ensure_screen_width(self):
        """
        Ensure all lines on a screen have proper width columns. Extra characters
        are truncated, missing characters are filled with whitespace.
        """
        for idx, line in enumerate(self.buffer):
            if len(line) > self.columns:
                self.buffer[idx] = line[:self.columns]
            elif len(line) < self.columns:
                self.buffer[idx] = line + take(self.columns - len(line),
                                               self.default_line)

        # If we're at the bottom of the history buffer and `DECTCEM`
        # mode is set -- show the cursor.
        self.cursor.hidden = not (
            abs(self.history.position - self.history.size) < self.lines and
            modes.DECTCEM in self.mode
        )

    def reset_history(self):
        self.history.top.clear()
        self.history.bottom.clear()
        self.history = self.history._replace(position=self.history.size)

    def reset(self):
        """
        Overloaded to reset screen history state: history position
        is reset to bottom of both queues;  queues themselves are
        emptied.
        """
        super(CustomHistoryScreen, self).reset()
        self.reset_history()

    def erase_in_display(self, how=0):
        """
        Overloaded to reset history state
        """
        super(CustomHistoryScreen, self).erase_in_display(how)

        if how == 3:
            self.reset_history()

    def index(self):
        """
        Overloaded to update top history with the removed lines
        """
        top, bottom = self.margins

        if self.cursor.y == bottom:
            self.history.top.append(self.buffer[top])

        super(CustomHistoryScreen, self).index()

    def reverse_index(self):
        """
        Overloaded to update bottom history with the removed lines
        """
        top, bottom = self.margins

        if self.cursor.y == top:
            self.history.bottom.append(self.buffer[bottom])

        super(CustomHistoryScreen, self).reverse_index()

    def prev_page(self):
        """
        Move the screen page up through the history buffer
        """
        if self.history.position > self.lines and self.history.top:
            mid = min(len(self.history.top),
                      int(math.ceil(self.lines * self.history.ratio)))

            self.history.bottom.extendleft(reversed(self.buffer[-mid:]))
            self.history = self.history \
                ._replace(position=self.history.position - self.lines)

            self.buffer[:] = list(reversed([
                self.history.top.pop() for _ in range(mid)
            ])) + self.buffer[:-mid]

            self.dirty = set(range(self.lines))

    def next_page(self):
        """
        Move the screen page down through the history buffer
        """
        if self.history.position < self.history.size and self.history.bottom:
            mid = min(len(self.history.bottom),
                      int(math.ceil(self.lines * self.history.ratio)))

            self.history.top.extend(self.buffer[:mid])
            self.history = self.history \
                ._replace(position=self.history.position + self.lines)

            self.buffer[:] = self.buffer[mid:] + [
                self.history.bottom.popleft() for _ in range(mid)
            ]

            self.dirty = set(range(self.lines))

        self.ensure_screen_width()

    def resize(self, lines=None, columns=None):
        lines = lines or self.lines
        columns = columns or self.columns

        # First resize the lines:
        line_diff = self.lines - lines

        # a) if the current display size is less than the requested
        #    size, add lines to the bottom.
        if line_diff < 0:
            self.buffer.extend(take(self.columns, self.default_line)
                               for _ in range(line_diff, 0))
        # b) if the current display size is greater than requested
        #    size, take lines off the top.
        elif line_diff > 0:
            # JW tweak - if we only have spaces in the bottom of the screen
            # remove those lines instead
            disp = self.display[-line_diff:]
            contents = "".join(disp)
            if contents.isspace():
                self.buffer[-line_diff:] = ()
            else:
                self.buffer[:line_diff] = ()

        # Then resize the columns:
        col_diff = self.columns - columns

        # a) if the current display size is less than the requested
        #    size, expand each line to the new size.
        if col_diff < 0:
            for y in range(lines):
                self.buffer[y].extend(take(abs(col_diff), self.default_line))
        # b) if the current display size is greater than requested
        #    size, trim each line from the right to the new size.
        elif col_diff > 0:
            for line in self.buffer:
                del line[columns:]

        self.lines, self.columns = lines, columns
        self.margins = Margins(0, self.lines - 1)

        # JW tweak - move cursor upwards if its out of bounds do not reset it
        self.ensure_bounds(use_margins=True)

        # Update tabstops to new screen size
        self.tabstops = set(range(8, self.columns, 8))

    def report_device_attributes(self, mode=0, **kwargs):

        if mode == 0 and not kwargs.get("private"):
            self.write_process_input("\x1b[" + "?6c")

    def report_device_status(self, mode):
        if mode == 5:    # Request for terminal status.
            self.write_process_input("\x1b[" + "0n")
        elif mode == 6:  # Request for cursor position.
            x = self.cursor.x + 1
            y = self.cursor.y + 1

            # "Origin mode (DECOM) selects line numbering."
            if modes.DECOM in self.mode:
                y -= self.margins.top
            self.write_process_input("{0}{1};{2}R".format("\x1b[", y, x))


def take(n, iterable):
    """Returns first n items of the iterable as a list."""
    return list(islice(iterable, n))


def convert_go_renditions_to_colormap(renditions, renditions_store, lines):
    out = []
    for line in renditions:
        line_rends = []
        for rendition in line:
            line_rends.append(renditions_store[rendition])
        out.append(line_rends)
    print(out)


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
        for char in line:
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
