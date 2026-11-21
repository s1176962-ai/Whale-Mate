"""Idle motion and speech for the AI-assistant mascot portrait.

The mascot is the transparent ``AI-assistant-icon.png`` the app already ships
(the assistant is named "Big Whale" / 大肥鱼 in the AI system prompt). This
module makes it pace left/right inside a Canvas with a soft vertical bob and a
small speech bubble that follows it, nudging the student to keep studying.

Design notes
------------
* The loop owns its ``after()`` handle instead of using ``Motion.schedule``:
  page navigation calls ``Motion.cancel()`` which would kill Motion-owned jobs,
  but the mascot should simply stop when its Canvas is destroyed.
* It still honours the in-app "motion off" setting: with motion off the portrait
  parks in place and the speech bubble shows a static full line (no typing).
* This Tk build cannot rotate or mirror Canvas images, so the walk is a calm
  horizontal pace plus a sine bob -- which suits a front-facing chibi best.
* Speech lines default to a small built-in bilingual pool; the app can inject
  API-generated lines via :meth:`inject_line` (they are queued first).
"""

import math
import random
import time
import tkinter as tk

from . import ui_tokens as T

# Built-in nudges. Used offline and as a fallback when the AI service is not
# configured or unavailable. Kept short so the bubble never covers the mascot.
LINE_POOL = {
    "zh": [
        "偷偷提醒：今天的目标还差一点点哦～",
        "别刷手机啦，先做两道题热热身？",
        "错题本在等你复习，它有点孤单了。",
        "学累了就站起来走走，回来我们继续。",
        "小提示：番茄钟 25 分钟，专注更有效。",
        "你上次进步很大，这次也一定行！",
        "先看一眼今天要学什么，我们慢慢来。",
        "会做就快做，不会就问我，别干坐着～",
    ],
    "en": [
        "Quick nudge: you're one question from today's goal!",
        "Put the phone down and do two warm-ups with me.",
        "Your mistake notebook feels lonely — come say hi.",
        "Tired? Take a short walk, then we'll keep going.",
        "Tip: try a 25-minute focus sprint.",
        "You improved a lot last time. Let's do it again!",
        "Peek at today's plan first — we'll go step by step.",
        "Stuck on something? Just ask me, don't just sit there!",
    ],
}


class MascotWalker:
    """Pace a transparent portrait and show a following speech bubble.

    Parameters
    ----------
    canvas : tk.Canvas
        Host canvas. The portrait is drawn near the bottom; ``top_pad`` pixels
        at the top are reserved for the speech bubble.
    image_path : str | pathlib.Path
        Path to the transparent PNG portrait.
    motion : Motion | None
        Shared Motion instance. When inactive the portrait rests centred and
        speech is shown statically.
    travel : float
        Fraction of the free horizontal space used for the walk (0..0.5).
    speed : float
        Horizontal pixels advanced per frame.
    bob : float
        Vertical bob amplitude in pixels.
    tick_ms : int
        Frame interval in milliseconds.
    top_pad : int
        Pixel height reserved at the top of the canvas for the bubble.
    language : str
        ``"zh"`` or ``"en"``; picks the built-in line pool.
    speech_interval_ms : int
        How often a new line is picked.
    type_ms : int
        Delay between typed characters in the bubble.
    """

    def __init__(
        self,
        canvas,
        image_path,
        motion=None,
        travel=0.34,
        speed=0.55,
        bob=4.0,
        tick_ms=33,
        top_pad=0,
        language="zh",
        speech_interval_ms=6500,
        type_ms=28,
    ):
        self.canvas = canvas
        self.image_path = str(image_path)
        self.motion = motion
        self.travel = float(travel)
        self.speed = float(speed)
        self.bob = float(bob)
        self.tick_ms = int(tick_ms)
        self.top_pad = max(0, int(top_pad))
        self.language = "en" if language == "en" else "zh"
        self.speech_interval_ms = int(speech_interval_ms)
        self.type_ms = int(type_ms)

        self._base = None
        self._scaled = None
        self._scale_key = None
        self._job = None
        self._x = None
        self._dir = 1
        self._phase = 0.0
        self._photo_refs = {}

        # speech state
        self._pools = {k: list(v) for k, v in LINE_POOL.items()}
        self._queue = {"zh": [], "en": []}  # API lines shown first
        self._line = ""
        self._shown = 0
        self._speech_at = 0.0
        self._type_at = 0.0
        self._last_line = ""
        self._speak_now()

    # -- image plumbing ---------------------------------------------------
    def _base_image(self):
        if self._base is None:
            try:
                self._base = tk.PhotoImage(master=self.canvas, file=self.image_path)
            except (tk.TclError, OSError):
                self._base = False
        return self._base or None

    def _portrait(self, target):
        """Return a cached subsample of the base sized to ``target`` px."""
        base = self._base_image()
        if base is None or target < 8:
            return None
        factor = max(1, int(round(max(base.width(), base.height()) / target)))
        if self._scale_key == factor and self._scaled is not None:
            return self._scaled
        photo = base.subsample(factor)
        self._scale_key = factor
        self._scaled = photo
        self._photo_refs[factor] = photo  # keep Tk from GC-ing the image
        return photo

    # -- speech -----------------------------------------------------------
    def set_language(self, language):
        """Switch line pool; the next line follows immediately."""
        language = "en" if language == "en" else "zh"
        if language != self.language:
            self.language = language
            self._speak_now()

    def inject_line(self, text, language=None):
        """Queue an externally generated (e.g. API) line to be shown soon.

        Queued lines take priority over the built-in pool and are consumed once.
        """
        text = (text or "").strip().replace("\n", " ")
        if not text:
            return
        key = (language or self.language)
        key = "en" if key == "en" else "zh"
        self._queue[key].insert(0, text[:90])

    def _next_line(self):
        q = self._queue[self.language]
        if q:
            return q.pop(0)
        pool = [x for x in self._pools[self.language] if x != self._last_line] or self._pools[self.language]
        return random.choice(pool)

    def _speak_now(self, initial=False):
        self._line = self._next_line()
        self._last_line = self._line
        self._shown = 0 if not initial else len(self._line)
        self._speech_at = time.monotonic()
        self._type_at = self._speech_at

    @staticmethod
    def _wrap(text, limit):
        """Wrap by words for English, by characters for CJK."""
        cjk = any("\u4e00" <= ch <= "\u9fff" for ch in text)
        lines, cur = [], ""
        if cjk:
            for ch in text:
                cur += ch
                if len(cur) >= limit:
                    lines.append(cur)
                    cur = ""
        else:
            for word in text.split():
                trial = f"{cur} {word}".strip()
                if len(trial) > limit and cur:
                    lines.append(cur)
                    cur = word
                else:
                    cur = trial
        if cur:
            lines.append(cur)
        return lines or [""]

    def _round_rect(self, cv, x1, y1, x2, y2, r, fill, outline):
        r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
        if r <= 0:
            cv.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline)
            return
        cv.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
        cv.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline="")
        for cx, cy, start in (
            (x1, y1, 90), (x2 - 2 * r, y1, 0),
            (x1, y2 - 2 * r, 180), (x2 - 2 * r, y2 - 2 * r, 270),
        ):
            cv.create_arc(cx, cy, cx + 2 * r, cy + 2 * r, start=start, extent=90,
                          style="pieslice", fill=fill, outline="")
        cv.create_arc(x1, y1, x2, y2, start=0, extent=360, style="arc", outline=outline)

    def _draw_bubble(self, cv, w, center_x, now):
        if self.top_pad < 18 or not self._line:
            return
        fill = T.SURFACE
        edge = T.AI_INPUT_EDGE
        ink = T.TEXT
        shown = self._line[: self._shown] if self._shown else ""
        if not shown:
            return
        limit = max(10, int((w - 28) / (8 if self.language == "zh" else 6)))
        lines = self._wrap(shown, limit)
        font = T.TYPE_CAPTION
        # measure using a temporary text item
        probe = cv.create_text(0, 0, text="\n".join(lines), font=font)
        box = cv.bbox(probe)
        cv.delete(probe)
        tw = (box[2] - box[0]) if box else 60
        th = (box[3] - box[1]) if box else 16
        bw = min(w - 12, tw + 26)
        bh = min(self.top_pad - 4, th + 16)
        bx1 = max(6, min(center_x - bw / 2, w - bw - 6))
        by1 = max(2, self.top_pad - bh - 2)
        bx2, by2 = bx1 + bw, by1 + bh
        self._round_rect(cv, bx1, by1, bx2, by2, min(12, bh / 2), fill, edge)
        # little tail pointing down toward the mascot
        tail_x = max(bx1 + 12, min(center_x, bx2 - 12))
        cv.create_polygon(tail_x - 6, by2 - 1, tail_x + 6, by2 - 1,
                          tail_x, by2 + 7, fill=fill, outline="")
        cv.create_text((bx1 + bx2) / 2, (by1 + by2) / 2, text="\n".join(lines),
                       font=font, fill=ink, justify="center")

    # -- animation --------------------------------------------------------
    def _motion_on(self):
        return self.motion is None or self.motion.active()

    def _draw(self):
        canvas = self.canvas
        if canvas is None or not canvas.winfo_exists():
            return
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w <= 8 or h <= 8:
            return
        canvas.delete("all")
        area_h = max(h - self.top_pad, 10)
        target = max(min(w - 10, area_h - 4), 10)
        photo = self._portrait(target)
        if photo is None:
            canvas.create_text(w / 2, h / 2, text="✦", fill=T.PRIMARY,
                               font=(T.FONT, 14, "bold"))
            return

        pw = photo.width()
        span = max(0.0, (w - pw) / 2)
        reach = span * self.travel
        on = self._motion_on()

        if reach <= 1:
            x = w / 2
        else:
            centre = w / 2
            if self._x is None:
                self._x = centre
            self._x = min(max(self._x, centre - reach), centre + reach)
            if on:
                self._x += self._dir * self.speed
                if self._x >= centre + reach:
                    self._x = centre + reach
                    self._dir = -1
                elif self._x <= centre - reach:
                    self._x = centre - reach
                    self._dir = 1
            x = self._x

        y = self.top_pad + area_h / 2
        if on and reach > 1:
            y += math.sin(self._phase) * self.bob
        canvas.create_image(x, y, image=photo, anchor="center")
        self._draw_bubble(canvas, w, x, time.monotonic())

    def _tick(self):
        self._job = None
        if self.canvas is None or not self.canvas.winfo_exists():
            return
        now = time.monotonic()
        on = self._motion_on()
        if on:
            if now - self._speech_at >= self.speech_interval_ms / 1000.0:
                self._speak_now()
            if self._shown < len(self._line) and now - self._type_at >= self.type_ms / 1000.0:
                self._shown += 1
                self._type_at = now
            self._phase += 0.16
        else:
            # static: show the full current line, no typing / rotation
            self._shown = len(self._line)
        self._draw()
        # When motion is explicitly off the mascot is static; redraw far less
        # often to avoid a busy 33ms loop. Language switches / injected lines
        # still repaint within 200ms, so behaviour stays responsive.
        static_slow = self.motion is not None and not self.motion.active()
        interval = 200 if static_slow else self.tick_ms
        self._job = self.canvas.after(interval, self._tick)

    # -- public API -------------------------------------------------------
    def start(self):
        if self._job is None and self.canvas is not None and self.canvas.winfo_exists():
            now = time.monotonic()
            self._speech_at = now
            self._type_at = now
            self._tick()

    def stop(self):
        if self._job is None:
            return
        try:
            self.canvas.after_cancel(self._job)
        except (tk.TclError, ValueError):
            pass
        self._job = None

    def redraw(self):
        """Repaint at the current position (used on resize / theme change)."""
        self._draw()
