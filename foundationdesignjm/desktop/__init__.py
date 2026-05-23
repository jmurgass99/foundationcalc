"""Native desktop application (Tkinter + embedded matplotlib).

Run with:

    python -m foundationdesignjm.desktop

No extra dependencies required: Tkinter ships with Python and
matplotlib is already a dependency of the library.
"""

from .app import FoundationDesignApp, main

__all__ = ["FoundationDesignApp", "main"]
