"""Badge wall and instant achievement unlock toasts."""

from __future__ import annotations

import tkinter as tk

from . import modern
from . import tokens as T
from .augment_ui import _rounded_points, _tier_palette, edge_colors, tier_pulse
from .augments import RARITY_LABELS

PALETTE_KEYS = ("silver", "gold", "prismatic", "demon")


class AchievementToast:
    """Stack of small borderless cards pinned inside the app window."""

    LIFETIME = 3600
    GAP = 10

    def __init__(self, app):
        self.app = app
        self._toasts = []
        self._pending = []  # root.after ids not yet fired

    def show(self, badges):
        for index, badge in enumerate(badges or []):
            job = {"id": None}

            def fire(b=badge, ref=job):
                if ref["id"] in self._pending:
                    self._pending.remove(ref["id"])
                self._one(b)

            try:
                job["id"] = self.app.root.after(index * 180, fire)
                self._pending.append(job["id"])
            except tk.TclError:
                pass

    def _one(self, badge):
        root = self.app.root
        if not root.winfo_exists():
            return
        palette = _tier_palette(badge.rarity)
        card = tk.Toplevel(root)
        card.overrideredirect(True)
        card.configure(bg=T.palette()["PAGE"])
        card.attributes("-topmost", True)
        try:
            card.transient(root)
        except tk.TclError:
            pass

        frame = tk.Frame(
            card, bg=palette["face"], highlightbackground=palette["edge"][0],
            highlightthickness=2,
        )
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        icon = tk.Label(
            frame, text=badge.icon, font=(T.FONT, 26),
            bg=palette["pill"], fg=palette["pill_ink"], width=2,
        )
        icon.pack(side="left", padx=(12, 10), pady=12)
        text = tk.Frame(frame, bg=palette["face"])
        text.pack(side="left", fill="both", expand=True, pady=10)
        p = T.palette()
        tk.Label(
            text, text=self.app.tr("成就解锁"), font=T.TYPE_CAPTION,
            bg=palette["face"], fg=p["TEXT_SECONDARY"], anchor="w",
        ).pack(anchor="w")
        tk.Label(
            text, text=self.app.tr(badge.name), font=T.TYPE_BODY_LARGE,
            bg=palette["face"], fg=p["TEXT"], anchor="w",
        ).pack(anchor="w")

        item = {"window": card, "started": 0, "glow": None}
        self._toasts.append(item)
        self._place()
        card.update_idletasks()
        if badge.rarity == "demon":
            self._toast_glow(item, frame, 0)
        self.app.motion.schedule(self.LIFETIME, lambda: self._dismiss(item))

    def _toast_glow(self, item, frame, phase):
        if not item["window"].winfo_exists() or item["glow"] is not None:
            return
        item["glow"] = phase
        try:
            frame.configure(highlightbackground=tier_pulse("demon", phase))
        except tk.TclError:
            item["glow"] = None
            return
        self.app.motion.schedule(150, lambda: self._toast_next_glow(item, frame))

    def _toast_next_glow(self, item, frame):
        phase = item["glow"]
        item["glow"] = None
        if phase is not None:
            self._toast_glow(item, frame, phase + 1)

    def _place(self):
        root = self.app.root
        try:
            rx, ry = root.winfo_rootx(), root.winfo_rooty()
            rw = root.winfo_width()
        except tk.TclError:
            return
        alive = [item for item in self._toasts if item["window"].winfo_exists()]
        self._toasts = alive
        for index, item in enumerate(alive):
            x = rx + rw - 340
            y = ry + 76 + index * (84 + self.GAP)
            item["window"].geometry(f"320x84+{x}+{y}")

    def dismiss_all(self):
        # Cancel delayed show() callbacks so a queued toast cannot pop up on
        # the next page after a fast "play again" / page switch.
        for job in list(self._pending):
            try:
                self.app.root.after_cancel(job)
            except (tk.TclError, ValueError):
                pass
        self._pending.clear()
        for item in list(self._toasts):
            self._dismiss(item)

    def _dismiss(self, item):
        if item in self._toasts:
            self._toasts.remove(item)
        window = item["window"]
        try:
            if window.winfo_exists():
                window.destroy()
        except tk.TclError:
            pass
        self._place()


class AchievementCard(tk.Canvas):
    """One badge on the wall: unlocked in colour, locked muted."""

    W = 300
    H = 132

    def __init__(self, parent, badge, unlocked, tr, height=None, motion=None):
        super().__init__(
            parent, width=T.px(self.W), height=T.px(height or self.H),
            bg=T.palette()["SURFACE"], highlightthickness=0, bd=0, takefocus=0,
        )
        self.badge = badge
        self.unlocked = unlocked
        self.tr = tr
        self.motion = motion
        self._edges = []
        self._glow_job = None
        self.bind("<Configure>", lambda event: self._draw())
        self.bind("<Destroy>", lambda _e: self._stop_glow())

    def _stop_glow(self):
        self._glow_job = None

    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 20 or h <= 20:
            return
        self.delete("all")
        palette = _tier_palette(self.badge.rarity)
        p = T.palette()
        # A muted tier-tinted edge even while locked, so the rarity is visible
        # before the badge is earned. Unlocked uses the full tier colour.
        edge = tier_pulse(self.badge.rarity, 0) if self.unlocked else \
            T.mix(p["SURFACE"], _locked_edge(self.badge.rarity), 0.45)
        face = palette["face"] if self.unlocked else p["HOVER"]
        modern.round_rect(self, 1, 1, w - 1, h - 1, T.px(T.RADIUS_CARD), fill=face)
        # Same segmented border as the augment cards: sample the rounded
        # perimeter into individual line segments so the tier shimmer can
        # travel around it. Every rarity gets a multi-segment coloured edge,
        # matching the cards rather than a single flat outline.
        points = _rounded_points(1, 1, w - 1, h - 1, T.px(T.RADIUS_CARD), steps=5)
        colors = palette["edge"]
        self._edges = []
        for index in range(len(points) - 1):
            target = edge if not self.unlocked else colors[index % len(colors)]
            item = self.create_line(
                points[index][0], points[index][1],
                points[index + 1][0], points[index + 1][1],
                fill=target, width=2,
            )
            self._edges.append((item, target))
        icon_bg = palette["pill"] if self.unlocked else \
            T.mix(p["SURFACE"], palette["pill"], 0.35)
        icon_fg = palette["pill_ink"] if self.unlocked else p["TEXT_MUTED"]
        modern.round_rect(
            self, T.px(12), T.px(12), T.px(58), T.px(58),
            T.px(T.RADIUS_CONTROL), fill=icon_bg,
        )
        self.create_text(
            T.px(35), T.px(35), text=self.badge.icon,
            font=(T.FONT, 22), fill=icon_fg,
        )
        # Both locked and unlocked cards reveal the achievement name and its
        # unlock condition (description) -- hiding the condition gives the
        # player no goal to work toward. Locked cards keep the muted tier tint
        # and a "locked" marker; unlocked ones add the full colour and check.
        tier_ink = palette["accent"] if self.unlocked else \
            T.mix(p["TEXT_MUTED"], _locked_edge(self.badge.rarity), 0.5)
        if self.unlocked:
            name_ink, name_font = p["TEXT"], T.TYPE_BODY_LARGE
            rarity_ink = p["TEXT_SECONDARY"]
            caption_ink = p["TEXT_SECONDARY"]
        else:
            name_ink, name_font = tier_ink, T.TYPE_BODY_LARGE
            rarity_ink = tier_ink
            caption_ink = p["TEXT_SECONDARY"]
        # Name and tier label are always visible; a locked card only dims them.
        self.create_text(
            T.px(72), T.px(16), text=self.tr(self.badge.name),
            font=name_font, anchor="nw", fill=name_ink,
        )
        self.create_text(
            T.px(72), T.px(42),
            text=self.tr(RARITY_LABELS[self.badge.rarity]),
            font=T.TYPE_CAPTION, anchor="nw", fill=rarity_ink,
        )
        # The unlock condition is never hidden -- without it there is no goal.
        # Wrap on word boundaries (Chinese has no spaces, so break per glyph
        # there) so English words are never split mid-word like "Hell-dif /
        # ficulty". Allow up to three lines now that the card is taller.
        caption = self.tr(self.badge.description)
        available_px = max(w - T.px(24), T.px(120))
        lines = _wrap_pixels(caption, available_px, T.TYPE_CAPTION, max_lines=3)
        self.create_text(
            T.px(12), T.px(72), text="\n".join(lines),
            font=T.TYPE_CAPTION, anchor="nw", fill=caption_ink,
        )
        if self.unlocked:
            self.create_text(
                w - T.px(12), T.px(16), text="\u2713",
                font=T.TYPE_BODY_LARGE, anchor="ne", fill=palette["edge"][0],
            )
        else:
            self.create_text(
                w - T.px(12), T.px(16), text=self.tr("未解锁"),
                font=T.TYPE_CAPTION, anchor="ne", fill=p["TEXT_MUTED"],
            )
        # Match the augment cards: prismatic and demon flow a highlight once
        # earned. A locked demon still glows faintly (dark tint) to advertise
        # the top tier; locked prismatic stays a static segmented edge.
        animate = self.badge.rarity in ("prismatic", "demon") and (
            self.unlocked or self.badge.rarity == "demon"
        )
        if animate and self.motion and self._glow_job is None:
            self._glow(0, self.unlocked)

    def _glow(self, phase, unlocked=True):
        if not self.winfo_exists() or self._glow_job is not None:
            return
        p = T.palette()
        self._glow_job = phase
        try:
            colors = edge_colors(self.badge.rarity, len(self._edges), phase)
            for index, (item, _target) in enumerate(self._edges):
                color = colors[index]
                if not unlocked:
                    color = T.mix(p["SURFACE"], color, 0.45)
                self.itemconfigure(item, fill=color)
        except tk.TclError:
            self._glow_job = None
            return
        self.motion.schedule(150, self._next_glow)

    def _next_glow(self):
        phase = self._glow_job
        self._glow_job = None
        if phase is not None:
            self._glow(phase + 1, self.unlocked)


def _locked_edge(rarity):
    """Base tier colour used to tint locked badges' borders."""
    palette = _tier_palette(rarity)
    return palette["edge"][0]


def _tk_measure(text, font):
    """Pixel width of ``text`` in ``font`` using the Tk font metrics."""
    root = _default_root()
    if root is None:
        return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text) * 7
    return int(root.tk.call("font", "measure", font, text))


def _default_root():
    try:
        return tk._default_root
    except AttributeError:
        return None


def _wrap_pixels(text, max_px, font, max_lines=3):
    """Wrap on word boundaries to fit ``max_px``, never splitting a word.

    English is tokenised on spaces; if a single word is itself wider than the
    line it is placed alone (and clipped by the canvas), avoiding the mid-word
    breaks that the old character-count wrapper produced. Chinese (no spaces)
    is wrapped per glyph. A hard newline in the source is always respected.
    """
    if not text:
        return [""]

    def fits(candidate):
        return _tk_measure(candidate, font) <= max_px

    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else current + " " + word
            if fits(candidate):
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            if fits(word):
                current = word
            else:
                # A very long word (or a CJK run): break it per glyph so it
                # still fits, but only as a last resort.
                chunk = ""
                for ch in word:
                    if chunk and not fits(chunk + ch):
                        lines.append(chunk)
                        chunk = ""
                    chunk += ch
                current = chunk
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
    return lines or [""]
