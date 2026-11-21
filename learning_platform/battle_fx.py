"""Battle health bars and damage-stage presentation.

The health bar is a vector Canvas widget so its fill can be tweened smoothly
without regenerating large images each frame. Damage staging swaps the mascot
portrait to the appropriate action frame and advances the round on a timer.
"""

from __future__ import annotations

import tkinter as tk

from . import modern
from . import tokens as T
from .motion import ease_in_out


class HealthBar(tk.Canvas):
    """A labelled rounded HP bar with an animated fill and numeric readout."""

    BAR_H = 12
    NAME_W = 108
    VALUE_W = 72
    HEART_GAP = 26
    BAR_MAX_W = 340

    def __init__(self, parent, name, maximum, motion=None, height=58, label_width=None, mirrored=False):
        super().__init__(
            parent,
            bg=T.palette()["SURFACE"],
            height=T.px(height),
            highlightthickness=0,
            bd=0,
            takefocus=0,
        )
        self.mirrored = mirrored
        self.name = name
        self.maximum = max(1, int(maximum))
        self.value = self.maximum
        self.displayed = float(self.maximum)
        self.motion = motion
        # Shared column width so both bars start at the same x; wide enough
        # for the longest name plus the heart, so nothing overlaps.  Use the
        # measured width verbatim when provided -- a hard NAME_W floor here
        # used to pin the heart back to a fixed x and defeat the alignment.
        self.label_width = int(label_width) if label_width else T.px(self.NAME_W)
        self.heart_x = self.label_width
        self.bar_geometry = None
        self.value_x = None
        self._flash = None
        self.bind("<Configure>", lambda event: self._draw())

    def _fill_color(self):
        ratio = self.value / self.maximum
        p = T.palette()
        if ratio <= 0.3:
            return p["ERROR"]
        if ratio <= 0.6:
            return p["WARNING"]
        return p["SUCCESS_FG"]

    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 60 or h <= 20:
            return
        p = T.palette()
        # Only clear the bar's own artwork. Floating combat labels (e.g. the
        # demon ×3) carry a "float" tag; mark everything as bar artwork, then
        # lift floats out of that tag so value-tween redraws never erase them.
        self.addtag("bar", "all")
        self.dtag("float", "bar")
        self.delete("bar")
        inset = T.px(8)
        bar_x, bar_x2 = inset, w - inset
        bar_h = T.px(self.BAR_H)
        bar_y = h - bar_h - T.px(8)
        self.bar_geometry = (bar_x, bar_y, bar_x2, bar_y + bar_h)
        self.heart_x = w - inset if self.mirrored else inset
        self.value_x = inset if self.mirrored else w - inset
        self.create_text(
            self.heart_x, T.px(14), text=self.name,
            font=T.TYPE_BUTTON, anchor="e" if self.mirrored else "w", fill=p["TEXT"],
        )
        self.create_text(
            self.value_x, T.px(14),
            text=f"{int(round(self.displayed))} / {self.maximum}",
            font=T.TYPE_CAPTION, anchor="w" if self.mirrored else "e",
            fill=p["TEXT_SECONDARY"],
        )
        modern.round_rect(
            self, bar_x, bar_y, bar_x2, bar_y + bar_h,
            radius=bar_h // 2, fill=p["TRACK"], outline=p["BORDER"], width=1,
        )
        ratio = max(0.0, min(1.0, self.displayed / self.maximum))
        length = (bar_x2 - bar_x) * ratio
        # Outside edges retain health; damage opens a gap toward the centre.
        left = bar_x2 - length if self.mirrored else bar_x
        right = bar_x2 if self.mirrored else bar_x + length
        self.fill_geometry = (left, bar_y, right, bar_y + bar_h)
        if length > 0:
            modern.round_rect(
                self, *self.fill_geometry, radius=min(bar_h // 2, length / 2),
                fill=self._flash or self._fill_color(),
            )

    def set_name(self, name):
        self.name = name
        self._draw()

    def set_value(self, value, animate=True, on_done=None):
        target = max(0, min(self.maximum, int(value)))
        self.value = target
        if not animate or not self.motion or not self.motion.active():
            self.displayed = float(target)
            self._flash = None
            self._draw()
            if on_done:
                on_done()
            return
        start = self.displayed
        if abs(target - start) < 0.01:
            self._draw()
            if on_done:
                on_done()
            return

        def frame(t):
            self.displayed = start + (target - start) * ease_in_out(t)
            self._draw()

        self.motion.tween(460, frame, on_done)

    def flash(self, color=None):
        """Brief tint pulse used when this side takes damage."""
        if not self.motion or not self.motion.active():
            return
        flash = color or T.palette()["ERROR"]

        def pulse(t):
            if not self.winfo_exists():
                return
            self._flash = flash if t < 0.5 else None
            self._draw()

        self.motion.tween(220, pulse, lambda: self._draw() if self.winfo_exists() else None)

    def float_text(self, text, color=None, duration=900):
        """Float a short label up from the bar and fade it out (e.g. '×3')."""
        if not self.winfo_exists():
            return
        color = color or T.palette()["ERROR"]
        w = self.winfo_width()
        x = w * (0.3 if self.mirrored else 0.7)
        y0 = T.px(34)
        item = self.create_text(
            x, y0, text=text, font=(T.FONT, 20, "bold"),
            fill=color, anchor="center", tags="float",
        )
        if not self.motion or not self.motion.active():
            self.after(duration, lambda: self._drop_float(item))
            return

        def frame(t):
            if not self.winfo_exists():
                return
            try:
                self.coords(item, x, y0 - T.px(12) * t)
                self.itemconfigure(item, fill=T.mix(T.palette()["BG"], color, max(0.0, 1.0 - t)))
            except tk.TclError:
                pass

        self.motion.tween(duration, frame, lambda: self._drop_float(item))

    def _drop_float(self, item):
        try:
            if self.winfo_exists():
                self.delete(item)
        except tk.TclError:
            pass
