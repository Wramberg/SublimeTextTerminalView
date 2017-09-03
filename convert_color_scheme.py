"""Functionality for converting a color scheme to a "TerminalView" scheme."""
import os
import plistlib
import sublime
from math import sqrt, sin, cos, pi, atan2, fabs, exp


# https://gist.github.com/fikr4n/368f2f2070e0f9a15fb4

def _square(x):
    return x * x


def cie76(L1_a1_b1, L2_a2_b2):
    L1, a1, b1 = L1_a1_b1
    L2, a2, b2 = L2_a2_b2
    return sqrt(_square(L1 - L2) + _square(a1 - a2) + _square(b1 - b2))


def cie94(L1_a1_b1, L2_a2_b2):
    """Calculate color difference by using CIE94 formulae

    See http://en.wikipedia.org/wiki/Color_difference or
    http://www.brucelindbloom.com/index.html?Eqn_DeltaE_CIE94.html.

    cie94(rgb2lab((255, 255, 255)), rgb2lab((0, 0, 0)))
    >>> 58.0
    cie94(rgb2lab(rgb(0xff0000)), rgb2lab(rgb('#ff0000')))
    >>> 0.0
    """

    L1, a1, b1 = L1_a1_b1
    L2, a2, b2 = L2_a2_b2

    C1 = sqrt(_square(a1) + _square(b1))
    C2 = sqrt(_square(a2) + _square(b2))
    delta_L = L1 - L2
    delta_C = C1 - C2
    delta_a = a1 - a2
    delta_b = b1 - b2
    delta_H_square = _square(delta_a) + _square(delta_b) - _square(delta_C)
    return sqrt(_square(delta_L) + _square(delta_C) / _square(1.0 + 0.045 * C1) +
                delta_H_square / _square(1.0 + 0.015 * C1))


def cie2000(L1_a1_b1, L2_a2_b2):
    """Calculate color difference by using CIE2000 formulae"""

    # blatantly copied from
    # http://www.brucelindbloom.com/index.html?Eqn_DeltaE_CIE2000.html
    L1, a1, b1 = L1_a1_b1
    L2, a2, b2 = L2_a2_b2
    C1 = sqrt(_square(a1) + _square(b1))
    C2 = sqrt(_square(a2) + _square(b2))
    Lbarprime = 0.5 * (L1 + L2)
    Cbar = 0.5 * (C1 + C2)
    Cbar_7 = Cbar**7.0
    G = 0.5 * (1.0 - sqrt(Cbar_7 / (Cbar_7 + 25.0**7.0)))
    a1prime = a1 * (1.0 + G)
    a2prime = a2 * (1.0 + G)
    C1prime = sqrt(_square(a1prime) + _square(b1))
    C2prime = sqrt(_square(a2prime) + _square(b2))
    Cbarprime = 0.5 * (C1prime + C2prime)
    h1prime = atan2(b1, a1prime)
    if h1prime < 0.0:
        h1prime += 2.0 * pi
    h2prime = atan2(b2, a2prime)
    if h2prime < 0.0:
        h2prime += 2.0 * pi
    if fabs(h1prime - h2prime) > pi:
        Hbarprime = 0.5 * (h1prime + h2prime + 2.0 * pi)
    else:
        Hbarprime = 0.5 * (h1prime + h2prime)
    # 30 deg == 0.523598776 rad
    #  6 deg == 0.104719755 rad
    # 63 deg == 1.09955743  rad
    T = 1.0 - \
        0.17 * cos(Hbarprime - 0.523598776) + \
        0.24 * cos(2.0 * Hbarprime) + \
        0.32 * cos(3.0 * Hbarprime + 0.104719755) - \
        0.20 * cos(4.0 * Hbarprime - 1.09955743)
    if fabs(h1prime - h2prime) <= pi:
        delta_hprime = h2prime - h1prime
    elif fabs(h1prime - h2prime) > pi and h2prime <= h1prime:
        delta_hprime = h2prime - h1prime + 2 * pi
    else:
        delta_hprime = h2prime - h1prime - 2 * pi

    delta_Lprime = L2 - L1
    delta_Cprime = C2prime - C1prime
    delta_Hprime = 2.0 * sqrt(C1prime * C2prime) * sin(delta_hprime * 0.5)

    S_L = 1.0 + 0.015 * _square(Lbarprime - 50.0) / sqrt(20.0 + _square(Lbarprime - 50.0))
    S_C = 1.0 + 0.045 * Cbarprime
    S_H = 1.0 + 0.015 * Cbarprime * T

    # 275 deg = 4.79965544 rad
    delta_theta = 30.0 * exp(-_square((Hbarprime - 4.79965544) / 25.0))

    Cbarprime_7 = Cbarprime**7.0
    R_C = 2.0 * sqrt(Cbarprime_7 / (Cbarprime_7 + 25.0**7))
    R_T = - R_C * sin(2.0 * delta_theta)

    K_L = 1.0  # default
    K_C = 1.0  # default
    K_H = 1.0  # default

    return sqrt(_square(delta_Lprime / (K_L * S_L)) + \
                _square(delta_Cprime / (K_C * S_C)) + \
                _square(delta_Hprime / (K_H * S_H)) + \
                R_T * (delta_Cprime / (K_C * S_C)) * (delta_Hprime / (K_H * S_H)))


def rgb2lab(R_G_B):
    """Convert RGB colorspace to Lab

    Adapted from http://www.easyrgb.com/index.php?X=MATH.
    """

    R, G, B = R_G_B

    # Convert RGB to XYZ

    var_R = R / 255.0        # R from 0 to 255
    var_G = G / 255.0        # G from 0 to 255
    var_B = B / 255.0        # B from 0 to 255

    if var_R > 0.04045:
        var_R = ((var_R + 0.055) / 1.055) ** 2.4
    else:
        var_R = var_R / 12.92
    if var_G > 0.04045:
        var_G = ((var_G + 0.055) / 1.055) ** 2.4
    else:
        var_G = var_G / 12.92
    if var_B > 0.04045:
        var_B = ((var_B + 0.055) / 1.055) ** 2.4
    else:
        var_B = var_B / 12.92

    var_R = var_R * 100.0
    var_G = var_G * 100.0
    var_B = var_B * 100.0

    # Observer. = 2°, Illuminant = D65
    X = var_R * 0.4124 + var_G * 0.3576 + var_B * 0.1805
    Y = var_R * 0.2126 + var_G * 0.7152 + var_B * 0.0722
    Z = var_R * 0.0193 + var_G * 0.1192 + var_B * 0.9505

    # Convert XYZ to L*a*b*

    var_X = X / 95.047         # ref_X =  95.047   Observer= 2°, Illuminant= D65
    var_Y = Y / 100.000        # ref_Y = 100.000
    var_Z = Z / 108.883        # ref_Z = 108.883

    if var_X > 0.008856:
        var_X = var_X ** (1.0/3.0)
    else:
        var_X = (7.787 * var_X) + (16.0 / 116.0)
    if var_Y > 0.008856:
        var_Y = var_Y ** (1.0/3.0)
    else:
        var_Y = (7.787 * var_Y) + (16.0 / 116.0)
    if var_Z > 0.008856:
        var_Z = var_Z ** (1.0/3.0)
    else:
        var_Z = (7.787 * var_Z) + (16.0 / 116.0)

    CIE_L = (116.0 * var_Y) - 16.0
    CIE_a = 500.0 * (var_X - var_Y)
    CIE_b = 200.0 * (var_Y - var_Z)
    return (CIE_L, CIE_a, CIE_b)

def hex_to_rgb(hexstring):
    """Convert a string representing a hex color to an RGB tuple."""

    # Forget about the alpha channel (that's possibly stored in hexstring[7:9]).
    return (int(hexstring[1:3], 16) / 255,
            int(hexstring[3:5], 16) / 255,
            int(hexstring[5:7], 16) / 255)


def rgb_to_hex(rgb):
    """Convert an RGB tuple to a hex string."""

    # Note that if a hexstring has an alpha channel, then that information is lost when you go
    # from hexstring -> rgb-tuple -> hexstring.
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0] * 255),
                                        int(rgb[1] * 255),
                                        int(rgb[2] * 255))


def norm2(vec3):
    """Compute the squared norm of a three-dimensional vector."""
    return vec3[0]**2 + vec3[1]**2 + vec3[2]**2


def distance2(a, b):
    """Compute the squared distance between two 3D vectors."""
    return norm2((a[0] - b[0], a[1] - b[1], a[2] - b[2]))


def next_color(hexstring):
    """Given a color string "#xxxxxy", returns its next color "#xxxxx{y+1}"."""

    # Forget about the alpha channel (that's possibly stored in hexstring[7:9]).
    h = int(hexstring[1:7], 16)

    # Return one more than we got, or one less if we're already at the max.
    return "#fffffe" if h == 0xffffff else "#{:06x}".format(h + 1)


# Also see: pyte/graphics.py
_name_from_index = ["black", "white", "red", "green", "blue", "brown", "magenta", "cyan"]

_rgb_from_name = {
    "black":   (0., 0., 0.),  # NOQA (silence flake8 linter about extraneous whitespace)
    "white":   (1., 1., 1.),  # NOQA

    "red":     (1., 0., 0.),  # NOQA
    "green":   (0., 1., 0.),  # NOQA
    "blue":    (0., 0., 1.),  # NOQA

    "cyan":    (0., 1., 1.),  # NOQA
    "magenta": (1., 0., 1.),  # NOQA
    "brown":   (1., 200/255., 0.)   # NOQA FIXME: Should be yellow...? This looks like a pyte issue.
}


def convert_color_scheme(infile, outfile):
    """Convert a color scheme from infile into outfile."""
    print("processing file", infile)
    base = plistlib.readPlistFromBytes(sublime.load_resource(infile).encode("utf-8"))
    scheme = base["settings"]

    # Fetch the "default" color.
    default = hex_to_rgb(scheme[0]["settings"]["background"])

    # Fetch the "black" color. In a dark scheme, it's actually white-ish.
    black = hex_to_rgb(scheme[0]["settings"]["foreground"])

    # Fetch the "selection" color. We make the assumption that the selection color is a suitable
    # background color for all other colors.
    selection = scheme[0]["settings"]["selection"]

    # Fetch all the other colors (start at 1).
    colors = set()
    for i in range(1, len(scheme)):
        item = scheme[i]
        scope = item.get("scope", None)
        if scope and "sublimelinter" in scope:
            print("skipping sublimelinter scope...")
            continue
        hexcolor = item.get("settings", {}).get("foreground", None)
        if hexcolor:
            # Note that colors is a set, so duplicates are removed while we iterate.
            colors.add(hex_to_rgb(hexcolor))

    # Convert into a list
    colors = list(colors)
    print("extracted", len(colors), "scope colors from scheme")

    # Convert them to Lab coordinates
    colors_lab = [rgb2lab(c) for c in colors]

    # Start processing our colors.
    terminal_colors = [default, black]
    while len(colors) < 6:
        print("adding extra black color so that we have enough colors to work with.")
        # we need at least six colors
        colors.append(black)

    # Skip the first two colors ("black" and "white").
    # This is the main "algorithm" of this function.
    for i in range(2, 8):
        best_index = -1
        smallest_distance = float("inf")
        terminal_color = _rgb_from_name[_name_from_index[i]]
        terminal_color = rgb2lab(terminal_color)
        for j, lab in enumerate(colors_lab):
            # We can choose from 4 different metrics:
            # - distance2 (using RGB coordinates),
            # - cie76     (using Lab coordinates),
            # - cie94     (using Lab coordinates),
            # - cie2000   (using Lab coordinates).
            d = cie94(terminal_color, lab)
            if d < smallest_distance:
                best_index = j
                smallest_distance = d
        terminal_colors.append(colors[best_index])
        del colors[best_index]  # Don't repeat colors.
        del colors_lab[best_index]

    # Convert our colors back to hex.
    terminal_colors = [rgb_to_hex(c) for c in terminal_colors]

    # Remove scopes from the color scheme.
    while len(scheme) > 1:
        del scheme[-1]

    # Now start adding in our own scopes.
    for i in range(0, 8):
        if i == 0:
            background = next_color(terminal_colors[i])
        else:
            background = terminal_colors[i]
        for j in range(0, 8):
            scope = "terminalview.{}_{}".format(_name_from_index[i], _name_from_index[j])
            # If the foreground color is the same as the background, use the "selection" color for
            # the foreground.
            foreground = selection if i == j else terminal_colors[j]
            settings = {"background": background, "foreground": foreground}
            scheme.append({"scope": scope, "settings": settings})

    # Save the results.
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    print("saving to", outfile)
    plistlib.writePlist(base, outfile)
