from . import GateOne


class GateOneTerminalEmulator():
    def __init__(self, cols, lines, hist, ratio):
        self._term = GateOne.Terminal(rows=lines, cols=cols)
        self._modified = True

    def feed(self, data):
        self._term.write(data)
        self._modified = True

    def resize(self, lines, cols):
        self._term.resize(rows=lines, cols=cols)
        self._modified = True

    def prev_page(self):
        self._term.scroll_up()

    def next_page(self):
        self._term.scroll_down()

    def dirty_lines(self):
        if not self._modified:
            return {}

        i = 0
        dirty_lines = {}
        for line in self._term.dump():
            dirty_lines[i] = line
            i = i + 1

        # convert_go_renditions_to_colormap(self._term.renditions, self._term.renditions_store, [])
        return dirty_lines

    def clear_dirty(self):
        self._modified = False

    def cursor(self):
        return self._term.cursorY, self._term.cursorX

    def color_map(self, lines):
        return {}

    def display(self):
        return self._term.dump()

    def modified(self):
        return self._modified

    def bracketed_paste_mode_enabled(self):
        # TODO Gateone doesnt seem to record this. But it supports callback for
        # custom escape sequences ?
        return False

    def application_mode_enabled(self):
        return self._term.expanded_modes['1']

    def nb_lines(self):
        return self._term.rows
