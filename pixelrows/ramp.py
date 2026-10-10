"""Colour ramps: one material from dark to light, built in OKLCH."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from .colour import fit_chroma, oklch_to_hex
from .errors import PixelRowsError


def _is_finite(value: object) -> bool:
    """Whether `value` is a finite number: an int or a float, and not a bool, nan or an infinity."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def even_lightness(steps: int, darkest: float = 0.30, lightest: float = 0.82) -> list[float]:
    """`steps` lightness values, evenly spaced from `darkest` to `lightest`. One step is the midpoint."""
    if not isinstance(steps, int) or steps < 1:
        raise PixelRowsError(f"even_lightness: steps must be a whole number of 1 or more, got {steps!r}")
    if steps == 1:
        return [(darkest + lightest) / 2]
    last = steps - 1
    return [darkest * (1 - i / last) + lightest * (i / last) for i in range(steps)]


@dataclass(frozen=True)
class Step:
    """One colour of a ramp."""

    lightness: float
    chroma: float
    hue: float
    hex: str
    asked_chroma: float
    clipped: bool

    def to_dict(self) -> dict[str, float | str | bool]:
        """
        The step as plain data, one key a field, with the numbers rounded for printing.

        The hue is rounded to 2 places and stays below 360, the others to 4.
        """
        return {
            "lightness": round(self.lightness, 4),
            "chroma": round(self.chroma, 4),
            "hue": round(self.hue, 2) % 360.0,
            "hex": self.hex,
            "asked_chroma": round(self.asked_chroma, 4),
            "clipped": self.clipped,
        }


def ramp(hue: float, chroma: float, lightness: Sequence[float] | None = None,
         hue_shift: float = 0.0, taper: float = 0.0) -> list[Step]:
    """
    One material from dark to light: a step for each lightness, in that order.

    `hue_shift` turns the hue by that many degrees a step, the dark steps one
    way and the light steps the other. `taper` is the share of chroma lost at
    the two ends. Chroma that sRGB cannot show is brought down to what it can,
    and the step is marked as clipped.

    Every argument is a finite number, `chroma` and `taper` from 0 to 1.
    `lightness` is a list or a tuple of at least one, each from 0 to 1.
    PixelRowsError naming the argument and its value otherwise.
    """
    for what, value in (("hue", hue), ("chroma", chroma), ("hue_shift", hue_shift), ("taper", taper)):
        if not _is_finite(value):
            raise PixelRowsError(f"ramp: {what} is {value!r}, not a finite number")
    if lightness is not None and not isinstance(lightness, (list, tuple)):
        raise PixelRowsError(f"ramp: lightness is {lightness!r}, not a list or a tuple")
    values = even_lightness(5) if lightness is None else list(lightness)
    if not values:
        raise PixelRowsError("ramp: no lightness values")
    for i, value in enumerate(values):
        if not _is_finite(value):
            raise PixelRowsError(f"ramp: lightness {i} is {value!r}, not a finite number")
        if not 0 <= value <= 1:
            raise PixelRowsError(f"ramp: lightness {i} is {value!r}, outside 0 to 1")
    if not chroma >= 0:
        raise PixelRowsError(f"ramp: chroma is {chroma!r}, it cannot be negative")
    if chroma > 1:
        raise PixelRowsError(f"ramp: chroma is {chroma!r}, it cannot be above 1")
    if not 0 <= taper <= 1:
        raise PixelRowsError(f"ramp: taper is {taper!r}, outside 0 to 1")
    mid = (len(values) - 1) / 2
    steps = []
    for i, value in enumerate(values):
        d = i - mid
        step_hue = (hue - d * hue_shift) % 360.0
        if step_hue >= 360.0:
            step_hue = 0.0
        if math.isnan(step_hue):
            raise PixelRowsError(f"ramp: hue {hue!r} turned by hue_shift {hue_shift!r} is too large to work out")
        asked = chroma * (1 - taper * abs(d) / mid) if mid else float(chroma)
        fitted = fit_chroma(value, asked, step_hue)
        steps.append(Step(
            lightness=float(value),
            chroma=fitted,
            hue=step_hue,
            hex=oklch_to_hex(value, fitted, step_hue),
            asked_chroma=asked,
            clipped=fitted < asked,
        ))
    return steps
