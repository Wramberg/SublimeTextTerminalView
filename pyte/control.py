# -*- coding: utf-8 -*-
"""
    pyte.control
    ~~~~~~~~~~~~

    This module defines simple control sequences, recognized by
    :class:`~pyte.streams.Stream`, the set of codes here is for
    ``TERM=linux`` which is a superset of VT102.

    :copyright: (c) 2011-2012 by Selectel.
    :copyright: (c) 2012-2017 by pyte authors and contributors,
                    see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""
from __future__ import unicode_literals

#: *Space*: Not suprisingly -- ``" "``.
SP = " "

#: *Null*: Does nothing.
NUL = "\x00"

#: *Bell*: Beeps.
BEL = "\x07"

#: *Backspace*: Backspace one column, but not past the begining of the
#: line.
BS = "\x08"

#: *Horizontal tab*: Move cursor to the next tab stop, or to the end
#: of the line if there is no earlier tab stop.
HT = "\x09"

#: *Linefeed*: Give a line feed, and, if :data:`pyte.modes.LNM` (new
#: line mode) is set also a carriage return.
LF = "\n"
#: *Vertical tab*: Same as :data:`LF`.
VT = "\x0b"
#: *Form feed*: Same as :data:`LF`.
FF = "\x0c"

#: *Carriage return*: Move cursor to left margin on current line.
CR = "\r"

#: *Shift out*: Activate G1 character set.
SO = "\x0e"

#: *Shift in*: Activate G0 character set.
SI = "\x0f"

#: *Cancel*: Interrupt escape sequence. If received during an escape or
#: control sequence, cancels the sequence and displays substitution
#: character.
CAN = "\x18"
#: *Substitute*: Same as :data:`CAN`.
SUB = "\x1a"

#: *Escape*: Starts an escape sequence.
ESC = "\x1b"

#: *Delete*: Is ignored.
DEL = "\x7f"

#: *Control sequence introducer*: An equivalent for ``ESC [``.
CSI = "\x9b"

#: *String terminator*.
ST = "\x9c"

#: *Operating system command*.
OSC = "\x9d"
