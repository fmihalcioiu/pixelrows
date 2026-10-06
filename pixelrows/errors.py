"""The one error the package raises for bad input."""


class PixelRowsError(ValueError):
    """Something in a sprite, a palette or a set file is wrong. The message says what and where."""
