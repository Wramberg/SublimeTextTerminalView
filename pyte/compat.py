# -*- coding: utf-8 -*-
"""
    pyte.compat
    ~~~~~~~~~~~

    Python version specific compatibility fixes.

    :copyright: (c) 2015-2017 by pyte authors and contributors,
                see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

import sys

if sys.version_info[0] == 2:
    from future_builtins import map

    range = xrange
    str = unicode
    chr = unichr

    def pass_through_str(data):
        """Decode :func:`bytes` to :func:`str` using pass-through encoding."""
        return "".join(chr(ord(ch)) for ch in data)
else:
    from builtins import map, range, str, chr

    def pass_through_str(data):
        """Decode :func:`bytes` to :func:`str` using pass-through encoding."""
        return "".join(map(chr, data))
