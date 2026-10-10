"""OKLab and OKLCH: colour as lightness, chroma and hue, to and from sRGB."""
from __future__ import annotations

import math

from .errors import PixelRowsError
from .palette import RGB, as_rgb, to_hex

# Bjorn Ottosson's OKLab matrices, as published.
_LINEAR_TO_LMS = (
    (0.4122214708, 0.5363325363, 0.0514459929),
    (0.2119034982, 0.6806995451, 0.1073969566),
    (0.0883024619, 0.2817188376, 0.6299787005),
)
_LMS_TO_LAB = (
    (0.2104542553, 0.7936177850, -0.0040720468),
    (1.9779984951, -2.4285922050, 0.4505937099),
    (0.0259040371, 0.7827717662, -0.8086757660),
)
_LAB_TO_LMS = (
    (1.0, 0.3963377774, 0.2158037573),
    (1.0, -0.1055613458, -0.0638541728),
    (1.0, -0.0894841775, -1.2914855480),
)
_LMS_TO_LINEAR = (
    (4.0767416621, -3.3077115913, 0.2309699292),
    (-1.2684380046, 2.6097574011, -0.3413193965),
    (-0.0041960863, -0.7034186147, 1.7076147010),
)

#: Below this chroma a colour is a grey and its hue is 0.
_NO_CHROMA = 1e-7

#: How far a linear channel may fall outside 0..1 and still count as in gamut.
#: The smallest of 1e-6, 1e-5 and 1e-4 that keeps all eight corners of the sRGB cube in.
_TOLERANCE = 1e-6

#: How many times fit_chroma halves its range.
_HALVINGS = 24


def _times(matrix: tuple[tuple[float, float, float], ...], x: float, y: float, z: float) -> tuple[float, float, float]:
    """A 3 by 3 matrix times a column of three."""
    first, second, third = (row[0] * x + row[1] * y + row[2] * z for row in matrix)
    return first, second, third


def _cube_root(value: float) -> float:
    return math.copysign(abs(value) ** (1 / 3), value)


def _decode(channel: int) -> float:
    """One sRGB channel, 0 to 255, as linear light."""
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _encode(value: float) -> int:
    """Linear light as one sRGB channel, clamped to 0..255 and rounded."""
    v = min(1.0, max(0.0, value))
    c = 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    return min(255, max(0, round(c * 255)))


def _wrap(degrees: float) -> float:
    """An angle brought into 0 <= h < 360."""
    h = degrees % 360.0
    return 0.0 if h >= 360.0 else h


def _finite(what: str, value: float) -> float:
    """`value` if it is a finite number: an int or a float, and not a bool, nan or an infinity."""
    if not isinstance(value, bool) and isinstance(value, (int, float)):
        try:
            if math.isfinite(value):
                return value
        except OverflowError:
            pass
    raise PixelRowsError(f"{what} must be a finite number, got {value!r}")


def srgb_to_oklab(rgb: RGB) -> tuple[float, float, float]:
    """An sRGB colour as OKLab (L, a, b)."""
    r, g, b = as_rgb(rgb)
    l, m, s = _times(_LINEAR_TO_LMS, _decode(r), _decode(g), _decode(b))
    return _times(_LMS_TO_LAB, _cube_root(l), _cube_root(m), _cube_root(s))


def oklab_to_linear(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    """
    OKLab as linear sRGB. A channel falls outside 0..1 when sRGB cannot show the colour.

    PixelRowsError when the numbers are too large to work out.
    """
    l, m, s = _times(_LAB_TO_LMS, lab[0], lab[1], lab[2])
    try:
        return _times(_LMS_TO_LINEAR, l ** 3, m ** 3, s ** 3)
    except OverflowError:
        raise PixelRowsError(f"OKLab {tuple(lab)!r} is too large to work out as sRGB") from None


def oklab_to_srgb(lab: tuple[float, float, float]) -> RGB:
    """OKLab as (r, g, b), each channel clamped to 0..255 and rounded."""
    r, g, b = oklab_to_linear(lab)
    return _encode(r), _encode(g), _encode(b)


def to_oklch(colour: str | RGB) -> tuple[float, float, float]:
    """A colour as (L, C, h): lightness 0 to 1, chroma, and hue in degrees from 0 up to 360."""
    l, a, b = srgb_to_oklab(as_rgb(colour))
    c = math.hypot(a, b)
    if c < _NO_CHROMA:
        return l, c, 0.0
    return l, c, _wrap(math.degrees(math.atan2(b, a)))


def oklch_to_oklab(l: float, c: float, h: float) -> tuple[float, float, float]:
    """Lightness, chroma and hue in degrees as OKLab (L, a, b). PixelRowsError unless each is a finite number."""
    _finite("lightness", l)
    _finite("chroma", c)
    angle = math.radians(_finite("hue", h))
    return l, c * math.cos(angle), c * math.sin(angle)


def in_gamut(l: float, c: float, h: float) -> bool:
    """Whether sRGB can show this colour."""
    return all(-_TOLERANCE <= v <= 1 + _TOLERANCE for v in oklab_to_linear(oklch_to_oklab(l, c, h)))


def fit_chroma(l: float, c: float, h: float) -> float:
    """The largest chroma up to `c` that sRGB can show at this lightness and hue."""
    if l <= 0 or l >= 1 or c <= 0:
        return 0.0
    if in_gamut(l, c, h):
        return c
    low, high = 0.0, c
    for _ in range(_HALVINGS):
        mid = (low + high) / 2
        if in_gamut(l, mid, h):
            low = mid
        else:
            high = mid
    return low


def oklch_to_hex(l: float, c: float, h: float) -> str:
    """Lightness, chroma and hue as '#rrggbb', with the chroma brought into gamut first."""
    return to_hex(oklab_to_srgb(oklch_to_oklab(l, fit_chroma(l, c, h), h)))


def lightness(colour: str | RGB) -> float:
    """The OKLab lightness of a colour, 0 for black to 1 for white."""
    return srgb_to_oklab(as_rgb(colour))[0]


def difference(a: str | RGB, b: str | RGB) -> float:
    """How far apart two colours are: their distance in OKLab."""
    return math.dist(srgb_to_oklab(as_rgb(a)), srgb_to_oklab(as_rgb(b)))
