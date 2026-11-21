"""Card-style augment draft UI: silver / gold / prismatic with light reveal.

The cards are plain Canvas items (no per-frame images), so the reveal only
moves and recolours a few dozen vectors per card. Motion is routed through the
shared Motion engine and is skipped entirely when animations are disabled.
"""

from __future__ import annotations

import math
import time
import tkinter as tk
import tkinter.font as tkfont

from . import modern
from . import ui_tokens as T
from .motion import ease_out_cubic

RAINBOW = ("#FF5D73", "#FFB454", "#5CE1A6", "#5B83FF", "#B06CFF")
# Demon tier: a deep-red border carrying several multi-coloured highlight
# streaks that run around it in parallel. Each streak is a burning tail:
# white hot head fading through blush, reds, black and brown to an ember-red
# tip before melting back into the base -- reads as black/white/red without
# the harsh zebra strobe of the other tiers.
DEMON_BASE = "#7A0C14"
DEMON_HIGHLIGHT = (
    "#FFFFFF",  # white-hot head
    "#FFD6D6",  # pale blush
    "#FF5A60",  # bright coral red
    "#D0141F",  # pure red
    "#5E070D",  # deep dark red
    "#140406",  # near black
    "#6E3A18",  # warm brown
    "#B4461E",  # ember / brown-red tail
)
DEMON_STREAKS = 3  # maximum highlight lines travelling the border at once
DEMON_PULSE = ("#7A0C14", "#B2131D", "#FF2D37", "#B2131D")
TIERS = ("silver", "gold", "prismatic", "demon")


def edge_colors(rarity, count, phase):
    """Per-segment border colours for an animated tier.

    Demon cards carry up to ``DEMON_STREAKS`` evenly spaced, multi-coloured
    highlights that advance together, so the border shows several distinct
    burning lines of light in motion instead of a single travelling dash.
    """
    if count <= 0:
        return []
    if rarity == "demon":
        colors = [DEMON_BASE] * count
        streak_len = len(DEMON_HIGHLIGHT)
        # A long tail needs room; place only as many streaks as fit while
        # still leaving a dark gap between neighbours (also matters on short
        # borders such as the compact AugmentBadge).
        active = min(DEMON_STREAKS, max(1, count // (streak_len + 1)))
        step = max(streak_len + 1, count // active)
        for streak in range(active):
            # Subtract the phase so the streaks travel counter-clockwise.
            head = (streak * step - phase) % count
            for offset, color in enumerate(DEMON_HIGHLIGHT):
                colors[(head + offset) % count] = color
        return colors
    return [RAINBOW[(index + phase) % len(RAINBOW)] for index in range(count)]


def tier_pulse(rarity, phase):
    """Single colour for widgets that only have one border (e.g. a toast)."""
    if rarity == "demon":
        return DEMON_PULSE[phase % len(DEMON_PULSE)]
    return _tier_palette(rarity)["edge"][0]


def _tier_palette(rarity):
    dark = T.theme_name() == "dark"
    if rarity == "silver":
        tint = "#B8C4D2" if dark else "#9AA6B5"
        edge = ["#D9E1EA", "#8F9BAA"] if dark else ["#8B96A5", "#C3CCD8"]
        pill = "#D9E1EA" if dark else "#8B96A5"
        pill_ink = "#1B2430" if dark else "#FFFFFF"
        accent = "#E6ECF4" if dark else "#4B5563"
    elif rarity == "gold":
        tint = "#C99A2E" if dark else "#D4A017"
        edge = ["#F7C948", "#B8860B"] if dark else ["#D4A017", "#F1C75B"]
        pill = "#E0A93B" if dark else "#C8912A"
        pill_ink = "#1B2430"
        accent = "#F5C542" if dark else "#9A6B00"
    elif rarity == "demon":
        tint = "#C4141E" if dark else "#B01019"
        edge = [DEMON_BASE, DEMON_HIGHLIGHT[1]]
        pill = "#0A0A0A"
        pill_ink = "#FFFFFF"
        accent = "#FF3B44" if dark else "#C4141E"
    else:
        tint = "#7C6BFF" if dark else "#6C5CE7"
        edge = list(RAINBOW)
        pill = "#6C5CE7" if dark else "#5B4BD6"
        pill_ink = "#FFFFFF"
        accent = "#B9A8FF" if dark else "#5B4BD6"
    return {
        "tint": tint,
        "edge": edge,
        "pill": pill,
        "pill_ink": pill_ink,
        "accent": accent,
        "face": T.mix(T.SURFACE, tint, 0.12 if dark else 0.07),
        "shadow": T.SHADOW_FAR,
    }


def _rounded_points(x1, y1, x2, y2, radius, steps=6):
    """Clockwise perimeter samples of a rounded rectangle."""
    r = max(0.0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = []
    for cx, cy, start in (
        (x2 - r, y1 + r, -90),
        (x2 - r, y2 - r, 0),
        (x1 + r, y2 - r, 90),
        (x1 + r, y1 + r, 180),
    ):
        for index in range(steps + 1):
            angle = math.radians(start + 90 * index / steps)
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    points.append(points[0])
    return points


def _wrap_by_width(text, font, max_width):
    lines = []
    current = ""
    for character in text:
        candidate = current + character
        if current and font.measure(candidate) > max_width:
            lines.append(current)
            current = character
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


class AugmentCard(tk.Canvas):
    """One selectable augment card with a staggered float-in reveal."""

    def __init__(self, parent, augment, tr, command=None, motion=None, height=172):
        super().__init__(
            parent,
            bg=T.BG,
            height=T.px(height),
            highlightthickness=0,
            bd=0,
            takefocus=0,
            cursor="hand2",
        )
        self.augment = augment
        self.tr = tr
        self.command = command
        self.motion = motion
        self.palette = _tier_palette(augment.rarity)
        self._faces = []
        self._body_items = []
        self._edges = []
        self._inks = []
        self._dy = 0
        self._rise = T.px(18)
        self._revealed = False
        self._revealing = False
        self._sized = False
        self.bind("<Configure>", self._draw)
        self.bind("<Button-1>", self._invoke)
        self.bind("<Enter>", lambda _e: self._hover(True))
        self.bind("<Leave>", lambda _e: self._hover(False))

    def _draw(self, _event=None):
        if self._revealing:
            return
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 40 or height <= 40:
            return
        self.delete("all")
        self._faces, self._body_items, self._edges, self._inks = [], [], [], []
        pad = T.px(T.SPACE_4)
        radius = T.px(T.RADIUS_CARD)
        face = self.palette["face"]
        hidden = T.BG

        before = set(self.find_all())
        modern.round_rect(
            self, pad, pad + T.px(4), width - pad, height - pad + T.px(4),
            radius, fill=hidden,
        )
        for item in set(self.find_all()) - before:
            self._faces.append((item, hidden, self.palette["shadow"]))
        before = set(self.find_all())
        modern.round_rect(
            self, pad, pad, width - pad, height - pad, radius, fill=hidden
        )
        for item in set(self.find_all()) - before:
            self._faces.append((item, hidden, face))
            self._body_items.append(item)

        points = _rounded_points(pad, pad, width - pad, height - pad, radius)
        colors = self.palette["edge"]
        for index in range(len(points) - 1):
            target = colors[index % len(colors)]
            item = self.create_line(
                points[index][0], points[index][1],
                points[index + 1][0], points[index + 1][1],
                fill=hidden, width=2,
            )
            self._edges.append((item, target))

        chip_h = T.px(24)
        chip_w = T.px(64)
        before = set(self.find_all())
        modern.round_rect(
            self, pad + T.px(2), pad + T.px(2), pad + chip_w,
            pad + T.px(2) + chip_h, T.px(T.RADIUS_CHIP), fill=hidden,
        )
        for item in set(self.find_all()) - before:
            self._inks.append((item, hidden, self.palette["pill"]))
        chip_text = self.create_text(
            pad + T.px(2) + chip_w / 2, pad + T.px(2) + chip_h / 2,
            text=self.tr(self.augment.rarity_label),
            font=T.TYPE_CAPTION, fill=hidden,
        )
        self._inks.append((chip_text, hidden, self.palette["pill_ink"]))

        title_y = pad + chip_h + T.px(T.SPACE_3)
        title = self.create_text(
            pad + T.px(2), title_y, text=self.tr(self.augment.name),
            font=T.TYPE_CARD, anchor="nw", fill=hidden,
        )
        self._inks.append((title, hidden, T.TEXT))

        body_font = tkfont.Font(font=T.TYPE_BODY)
        lines = _wrap_by_width(
            self.tr(self.augment.description), body_font, width - pad * 2
        )
        desc = self.create_text(
            pad + T.px(2), title_y + T.px(26), text="\n".join(lines),
            font=T.TYPE_BODY, anchor="nw", fill=hidden,
        )
        self._inks.append((desc, hidden, T.TEXT_SECONDARY))

        choose_y = height - pad - T.px(26)
        choose = self.create_text(
            pad + T.px(2), choose_y, text=self.tr("选择这张"),
            font=T.TYPE_BUTTON, anchor="nw", fill=hidden,
        )
        self._inks.append((choose, hidden, self.palette["accent"]))

        if not self._sized:
            self._sized = True
            needed = choose_y + T.px(26) + pad
            if needed > height:
                self.configure(height=needed)
                return

        if self._revealed:
            self._paint(1.0)
            offset = self._dy
            if offset:
                self.move("all", 0, -offset)
                self._dy = 0

    def _paint(self, progress):
        t = max(0.0, min(1.0, progress))
        for item, start, target in self._faces:
            self.itemconfigure(item, fill=T.mix(start, target, t))
        for item, target in self._edges:
            self.itemconfigure(item, fill=T.mix(T.BG, target, t))
        for item, start, target in self._inks:
            self.itemconfigure(item, fill=T.mix(start, target, t))

    def _frame(self, progress):
        if not self.winfo_exists():
            return
        self._paint(progress)
        target = int(self._rise * (1 - progress))
        delta = target - self._dy
        if delta:
            self.move("all", 0, delta)
            self._dy = target

    def _after_reveal(self):
        self._revealing = False
        self._revealed = True
        if self.augment.rarity in ("prismatic", "demon") and self.motion:
            self._shimmer(0)

    def _shimmer(self, phase):
        if not self.winfo_exists() or not self.motion:
            return
        colors = edge_colors(self.augment.rarity, len(self._edges), phase)
        for (item, _target), color in zip(self._edges, colors):
            self.itemconfigure(item, fill=color)
        self.motion.schedule(150, lambda: self._shimmer(phase + 1))

    def _run_reveal(self, started, duration=420):
        """Wall-clock reveal; independent of the global motion toggle.

        Only three small cards are touched, and every step is registered with
        Motion so :meth:`app.clear` still cancels it on navigation.
        """
        if not self.winfo_exists() or not self.motion:
            return
        elapsed = (time.monotonic() - started) * 1000.0
        progress = min(1.0, elapsed / float(duration))
        self._frame(ease_out_cubic(progress))
        if progress < 1.0:
            self.motion.schedule(16, lambda: self._run_reveal(started, duration))
        else:
            self._after_reveal()

    def reveal(self, delay=0):
        if not self.winfo_exists() or not self.motion:
            return
        # Cards are packed just before this call; make sure the first real
        # geometry is available before locking out further Configure redraws.
        if not self.find_all():
            self.update_idletasks()
            self._draw()
            if not self.find_all():
                self.update_idletasks()
                self._draw()
        if not self.find_all():
            return
        self._revealing = True
        self.move("all", 0, self._rise)
        self._dy = self._rise
        self._paint(0.0)

        def start():
            if self.winfo_exists():
                self._run_reveal(time.monotonic())

        if delay:
            self.motion.schedule(delay, start)
        else:
            start()

    def _hover(self, entering):
        if not self._revealed or not self.winfo_exists():
            return
        for item in self._body_items:
            target = self.palette["face"]
            color = T.mix(target, self.palette["tint"], 0.08 if entering else 0)
            self.itemconfigure(item, fill=color)

    def _invoke(self, _event=None):
        if self.command:
            self.command()


class AugmentBadge(tk.Canvas):
    """Compact tier-coloured strip used on each battle round and the results page."""

    def __init__(self, parent, augment, tr, motion=None, height=66):
        super().__init__(
            parent,
            bg=T.BG,
            height=T.px(height),
            highlightthickness=0,
            bd=0,
            takefocus=0,
        )
        self.augment = augment
        self.tr = tr
        self.motion = motion
        self.palette = _tier_palette(augment.rarity)
        self._edges = []
        self._shimmering = False
        self._sized = False
        self.bind("<Configure>", self._draw)

    def _draw(self, _event=None):
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 60 or height <= 24:
            return
        self.delete("all")
        self._edges = []
        pad = T.px(T.SPACE_2)
        radius = T.px(T.RADIUS_CHIP)
        modern.round_rect(self, 1, 1, width - 1, height - 1, radius, fill=self.palette["face"])
        points = _rounded_points(1, 1, width - 1, height - 1, radius, steps=4)
        colors = self.palette["edge"]
        for index in range(len(points) - 1):
            color = colors[index % len(colors)]
            item = self.create_line(
                points[index][0], points[index][1],
                points[index + 1][0], points[index + 1][1],
                fill=color, width=2,
            )
            self._edges.append((item, color))

        chip_w, chip_h = T.px(58), T.px(22)
        chip_x = pad + T.px(4)
        chip_y = (height - chip_h) // 2
        modern.round_rect(
            self, chip_x, chip_y, chip_x + chip_w, chip_y + chip_h,
            T.px(T.RADIUS_CHIP), fill=self.palette["pill"],
        )
        self.create_text(
            chip_x + chip_w / 2, chip_y + chip_h / 2,
            text=self.tr(self.augment.rarity_label),
            font=T.TYPE_CAPTION, fill=self.palette["pill_ink"],
        )

        text_x = chip_x + chip_w + T.px(T.SPACE_3)
        title = self.tr("海克斯强化：{0}", self.tr(self.augment.name))
        self.create_text(
            text_x, pad, text=title, font=T.TYPE_BODY_LARGE,
            anchor="nw", fill=T.TEXT,
        )
        caption = tkfont.Font(font=T.TYPE_CAPTION)
        lines = _wrap_by_width(
            self.tr(self.augment.description), caption,
            max(width - text_x - pad, 40),
        )
        self.create_text(
            text_x, pad + T.px(21), text="\n".join(lines),
            font=T.TYPE_CAPTION, anchor="nw", fill=T.TEXT_SECONDARY,
        )

        if not self._sized:
            self._sized = True
            needed = pad + T.px(21) + len(lines) * caption.metrics("linespace") + pad + 4
            if needed > height:
                self.configure(height=needed)
                return

        if self.augment.rarity in ("prismatic", "demon") and not self._shimmering:
            self._shimmering = True
            self._shimmer(0)

    def _shimmer(self, phase=0):
        if not self.winfo_exists() or not self.motion:
            return
        colors = edge_colors(self.augment.rarity, len(self._edges), phase)
        try:
            for (item, _color), color in zip(self._edges, colors):
                self.itemconfigure(item, fill=color)
        except tk.TclError:
            return
        self.motion.schedule(150, lambda: self._shimmer(phase + 1))
