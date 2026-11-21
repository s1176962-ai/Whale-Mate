"""Segmented score cards for the battle result dock.

A :class:`ScoreCard` turns a ``BattleScore`` (correct + speed + bonus = total)
into a row of small framed segments, so the player can read where every point
came from at a glance. Pure Canvas vectors keep it crisp at any DPI and avoid
per-frame images; colours are read from the active palette at draw time.
"""

from __future__ import annotations

import tkinter as tk

from . import modern
from . import tokens as T


class ScoreCard(tk.Canvas):
    """One combatant's score broken into framed segments.

    Layout (one row)::

          correct   speed   bonus   total
          [ 100 ] + [ 50 ] + [ 0 ] = [ 150 ]

    The player name is intentionally not drawn here: the health bar above
    already labels each combatant, so repeating it would be noise.
    """

    SEGMENTS = ("correct", "time", "extra", "total")
    H = 58
    SEG_W = 44
    SEG_H = 20
    GAP = 10
    PAD = 6
    LABEL_H = 20

    def __init__(self, parent, name, tr, accent=None, height=None, width=None, motion=None, mirrored=False):
        # Width must be explicit: a Canvas with no width defaults to ~478px in
        # Tk, which would crush the centre dialog column in the result dock.
        default_w = len(self.SEGMENTS) * self.SEG_W + (len(self.SEGMENTS) - 1) * self.GAP + self.PAD * 2
        super().__init__(
            parent,
            width=T.px(width or default_w),
            height=T.px(height or self.H),
            bg=T.palette()["SURFACE"],
            highlightthickness=0,
            bd=0,
            takefocus=0,
        )
        self.mirrored = mirrored
        self.name = name
        self.tr = tr
        self.accent = accent
        self.score = None  # BattleScore or None
        self.motion = motion
        self.bind("<Configure>", lambda _e: self._draw())

    def set_score(self, score, accent=None):
        """Set the score to display and redraw."""
        self.score = score
        if accent is not None:
            self.accent = accent
        self._draw()

    def clear(self):
        """Reset to the empty 'awaiting result' state."""
        self.score = None
        self._draw()

    def _segment_values(self):
        if self.score is None:
            return None
        return (
            int(self.score.correct),
            int(self.score.time),
            int(self.score.extra),
            int(self.score.total),
        )

    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 20 or h <= 20:
            return
        self.delete("all")
        p = T.palette()
        accent = self.accent or p["PRIMARY"]

        values = self._segment_values()
        labels = (
            self.tr("正确"),
            self.tr("速度"),
            self.tr("加成"),
            self.tr("总分"),
        )
        connectors = ("+", "+", "=")
        # Correct / speed / bonus use the palette; the total uses the tier
        # accent so the final number reads as the headline.
        fills = (p["SUCCESS_BG"], p["INFO_BG"], p["RAISED"], accent)
        inks = (p["SUCCESS_FG"], p["INFO"], p["TEXT_SECONDARY"], p["ON_PRIMARY"])

        seg_w = T.px(self.SEG_W)
        seg_h = T.px(self.SEG_H)
        gap = T.px(self.GAP)
        label_h = T.px(self.LABEL_H)
        pad = T.px(self.PAD)
        width = seg_w * 4 + gap * 3
        # Horizontally centre the whole row inside the card.
        x0 = max(pad, (w - width) / 2)
        # Caption goes ABOVE its box; the box row is vertically centred in the
        # remaining space. Frames are always drawn, even before the result, so
        # the dock never collapses into a lone "awaiting" sentence.
        y0 = pad + label_h
        y1 = y0 + seg_h

        for index in range(4):
            slot = 3 - index if self.mirrored else index
            x = x0 + slot * (seg_w + gap)
            ink = inks[index]
            # Description above the matching frame, centred on it.
            self.create_text(
                x + seg_w / 2, pad,
                text=labels[index], font=T.TYPE_FOOT, anchor="n",
                fill=p["TEXT_MUTED"],
            )
            modern.round_rect(
                self, x, y0, x + seg_w, y1,
                radius=T.px(6), fill=fills[index],
                outline=ink if index == 3 else p["BORDER_LIGHT"],
                width=2 if index == 3 else 1,
            )
            # While awaiting the result the frames stay visible with a dash.
            value = str(values[index]) if values is not None else "·"
            self.create_text(
                x + seg_w / 2, (y0 + y1) / 2,
                text=value, font=T.TYPE_BUTTON, anchor="center",
                fill=ink if values is not None else p["TEXT_MUTED"],
            )
            if index < len(connectors):
                self.create_text(
                    x - gap / 2 if self.mirrored else x + seg_w + gap / 2, (y0 + y1) / 2,
                    text=connectors[index], font=T.TYPE_BODY,
                    anchor="center", fill=p["TEXT_SECONDARY"],
                )
