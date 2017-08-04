"""
Cache classes for the ST3 view that can be used as an alternative to some of the
ST3 API functions (as long as they are kept up to date of course).
"""

class SublimeViewContentCache():
    """
    Sublime view content cache. Keep this up to date with any changes you make
    to a views content and it will perform much faster than its ST3 API
    equivalent.
    """
    def __init__(self):
        self._buffer_contents = {}

    def update_line(self, line_no, content):
        self._buffer_contents[line_no] = content

    def delete_line(self, line_no):
        if line_no in self._buffer_contents:
            del self._buffer_contents[line_no]

    def get_line(self, line_no):
        if line_no in self._buffer_contents:
            return self._buffer_contents[line_no]
        return None

    def has_line(self, line_no):
        return line_no in self._buffer_contents

    def get_line_start_and_end_points(self, line_no):
        start_point = 0

        # Sum all lines leading up to the line we want the start point to
        for i in range(line_no):
            if i in self._buffer_contents:
                line_len = len(self._buffer_contents[i])
                start_point = start_point + line_len

        # Add length of line to the end_point
        end_point = start_point
        if line_no in self._buffer_contents:
            line_len = len(self._buffer_contents[line_no])
            end_point = end_point + line_len

        return (start_point, end_point)


class SublimeViewRegionCache():
    """
    Sublime view region cache. Keep this up to date with any changes you make
    to a views regions and it will perform much faster than its ST3 API
    equivalent.
    """
    def __init__(self):
        self._buffer_regions = {}

    def add(self, line_no, key):
        if line_no in self._buffer_regions:
            self._buffer_regions[line_no].append(key)
        else:
            self._buffer_regions[line_no] = [key]

    def get_line(self, line_no):
        if line_no in self._buffer_regions:
            return self._buffer_regions[line_no]
        return None

    def delete_line(self, line_no):
        if line_no in self._buffer_regions:
            del self._buffer_regions[line_no]

    def has_line(self, line_no):
        return line_no in self._buffer_regions
