"""Optional, interruptible Tk after() motion. Scoring never waits on it."""

import time
import tkinter as tk

from . import ui_tokens as T


def ease_out_cubic(t):
    """Fast start, gentle settle. ``t`` is clamped to 0..1."""
    t = max(0.0, min(1.0, float(t)))
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    """Symmetric ease for colour fades and value counters."""
    t = max(0.0, min(1.0, float(t)))
    return 3 * t * t - 2 * t * t * t


class Motion:
    def __init__(self, root):
        self.root = root
        self.enabled = True
        self._jobs = []
        self._overlay = None
        self._overlays = set()

    def active(self):
        try:
            return bool(self.enabled and self.root.winfo_exists() and self.root.winfo_viewable())
        except tk.TclError:
            return False

    def cancel(self):
        for job in list(self._jobs):
            try:
                self.root.after_cancel(job)
            except tk.TclError:
                pass
        self._jobs.clear()
        for overlay in tuple(self._overlays):
            self._drop_overlay(overlay)

    def schedule(self, delay, callback):
        job = {"id": None}

        def run():
            if job["id"] in self._jobs:
                self._jobs.remove(job["id"])
            try:
                if not self.root.winfo_exists():
                    return
            except tk.TclError:
                return
            callback()

        job["id"] = self.root.after(delay, run)
        self._jobs.append(job["id"])
        return job["id"]

    def _track_overlay(self, overlay):
        self._overlays.add(overlay)
        self._overlay = overlay

    def _drop_overlay(self, overlay=None):
        """Destroy ``overlay`` (or the current one) without touching others.

        Callbacks capture their own overlay so a delayed cleanup can never
        destroy a different animation's layer that replaced it in the slot.
        """
        if overlay is None:
            overlay = self._overlay
        if overlay is None:
            return
        self._overlays.discard(overlay)
        if self._overlay is overlay:
            self._overlay = None
        try:
            if overlay.winfo_exists():
                overlay.destroy()
        except tk.TclError:
            pass

    def fade_in(self, host, duration=220):
        if not self.active() or not host.winfo_exists():
            return
        overlay = tk.Frame(host, bg=T.BG)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._track_overlay(overlay)
        self.schedule(duration, lambda: self._drop_overlay(overlay))

    def circle_transition(self, host, callback, x=None, y=None, color=None):
        color = color or T.SUCCESS_BG
        if not self.active() or not host.winfo_exists():
            callback()
            return
        host.update_idletasks()
        width = max(host.winfo_width(), 1)
        height = max(host.winfo_height(), 1)
        cx = width // 2 if x is None else x
        cy = height // 2 if y is None else y
        overlay = tk.Canvas(host, bg=T.BG, highlightthickness=0, bd=0)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._track_overlay(overlay)
        max_radius = int((width**2 + height**2) ** 0.5) + 40

        def expand(radius=0):
            if not overlay.winfo_exists():
                callback()
                return
            overlay.delete("all")
            overlay.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                fill=color,
                outline="",
            )
            if radius < max_radius:
                self.schedule(12, lambda: expand(radius + 55))
            else:
                self._drop_overlay(overlay)
                callback()

        expand()

    def slide_prepare(self, host, direction="left"):
        """Brief nudge before a page rebuild. Returns False if skipped."""
        if not self.active() or not host.winfo_exists():
            return False
        try:
            host.place_configure(x=-28 if direction == "left" else 28)
        except tk.TclError:
            return False
        return True

    def submit_feedback(self, button, ok, on_done):
        """Text-only stages: clear → mark → restore label. Never blocks scoring."""
        mark = "OK" if ok else "X"
        if not self.active() or not button.winfo_exists():
            on_done()
            return

        def stage(step=0):
            if not button.winfo_exists():
                on_done()
                return
            if step == 0:
                button.configure(text="")
                self.schedule(100, lambda: stage(1))
            elif step == 1:
                button.configure(text=mark)
                self._spark(button, ok)
                self.schedule(180, lambda: stage(2))
            else:
                on_done()

        stage()

    def _spark(self, near, ok):
        if not self.active() or not near.winfo_exists():
            return
        try:
            parent = near.nametowidget(near.winfo_parent())
        except tk.TclError:
            return
        color = T.SUCCESS_FG if ok else T.ERROR
        canvas = tk.Canvas(parent, width=120, height=48, bg=T.BG, highlightthickness=0, bd=0)
        canvas.place(in_=near, relx=0.5, rely=0, anchor="s")
        self._track_overlay(canvas)
        dots = []
        for dx, dy in ((-20, 20), (-6, 8), (8, 6), (22, 18), (0, 28)):
            dots.append(
                canvas.create_oval(60 + dx, dy, 60 + dx + 6, dy + 6, fill=color, outline="")
            )

        def tick(n=0):
            if not canvas.winfo_exists():
                return
            for item in dots:
                canvas.move(item, 0, -2 if n < 4 else 1)
            if n < 8:
                self.schedule(28, lambda: tick(n + 1))
            else:
                self._drop_overlay(canvas)

        tick()

    def grow_progress(self, bar, target):
        if not bar.winfo_exists():
            return
        if not self.active():
            bar.configure(value=target)
            return
        current = [float(bar.cget("value") or 0)]
        steps = max(int(abs(target - current[0]) * 5), 1)
        delta = (target - current[0]) / steps

        def tick(left=steps):
            if not bar.winfo_exists():
                return
            if left <= 0:
                bar.configure(value=target)
                return
            current[0] += delta
            bar.configure(value=current[0])
            self.schedule(28, lambda: tick(left - 1))

        tick()

    def roll_count(self, label, formatter, start, end):
        if not label.winfo_exists():
            return
        if not self.active() or start == end:
            label.configure(text=formatter(end))
            return
        current = [float(start)]
        steps = min(abs(end - start), 12) or 1
        delta = (end - start) / steps

        def tick(left=steps):
            if not label.winfo_exists():
                return
            if left <= 0:
                label.configure(text=formatter(end))
                return
            current[0] += delta
            label.configure(text=formatter(int(round(current[0]))))
            self.schedule(24, lambda: tick(left - 1))

        tick()

    def paint_path(self, canvas, total, current, done=False):
        if not canvas.winfo_exists():
            return
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1)
        if width < 20:
            canvas.after(16, lambda: self.paint_path(canvas, total, current, done))
            return
        total = max(total, 1)
        pad = 16
        span = max(width - pad * 2, 1)
        y = 14
        for index in range(total):
            x = pad + span * index / max(total - 1, 1)
            filled = index < current or (done and index < total)
            color = T.PRIMARY if filled else T.BORDER
            if index < total - 1:
                x2 = pad + span * (index + 1) / max(total - 1, 1)
                canvas.create_line(
                    x + 7,
                    y,
                    x2 - 7,
                    y,
                    fill=T.PRIMARY if index < current - (0 if done else 1) else T.BORDER,
                    width=3,
                )
            canvas.create_oval(
                x - 7,
                y - 7,
                x + 7,
                y + 7,
                fill=T.SURFACE if not filled else T.PRIMARY,
                outline=color,
                width=2,
            )

    # ------------------------------------------------------------------
    # General-purpose tweens (Qt-style properties, without Qt).
    # ------------------------------------------------------------------
    def tween(self, duration, on_update, on_done=None, easing=None):
        """Drive ``on_update(t)`` from t=0 to t=1 over ``duration`` ms.

        Interruptible via :meth:`cancel` and a no-op (jumps to the final
        frame) when motion is disabled or the root is gone.
        """
        if not self.active():
            on_update(1.0)
            if on_done:
                on_done()
            return
        ease = easing or ease_out_cubic
        steps = max(3, int(duration / 16))

        def frame(step=0):
            t = min(1.0, step / steps)
            try:
                on_update(ease(t))
            except tk.TclError:
                return
            if t < 1.0:
                self.schedule(16, lambda: frame(step + 1))
            elif on_done:
                on_done()

        frame(0)

    def recolor(self, widget, option, start, end, duration=200, easing=None):
        """Animate any Tk colour option (``bg``/``fg``) between two hexes."""
        if not self.active() or not widget.winfo_exists():
            return

        def frame(t):
            if not widget.winfo_exists():
                return
            try:
                widget.configure(**{option: T.mix(start, end, t)})
            except tk.TclError:
                pass

        self.tween(duration, frame, easing=easing or ease_in_out)

    def color_wash(self, host, old_color, new_color, duration=280):
        """Wash a host from its old palette colour to the new one.

        Used on theme change so the swap reads as a soft crossfade rather than
        an instant repaint. The wash covers the rebuild and removes itself.
        """
        if not self.active() or not host.winfo_exists():
            return
        # Do NOT drop the current overlay here: apply_theme() rebuilds the
        # screen (creating a fade_overlay Toplevel) right before calling us.
        # Each animation owns and cleans up its own layer via a captured ref.
        overlay = tk.Frame(host, bg=old_color)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._track_overlay(overlay)

        def frame(t):
            if not overlay.winfo_exists():
                return
            try:
                overlay.configure(bg=T.mix(old_color, new_color, t))
            except tk.TclError:
                pass

        self.tween(duration, frame, lambda: self._drop_overlay(overlay), ease_in_out)

    def fade_overlay(self, host, duration=380, color=None, easing=None):
        """Fade just ``host``'s screen rectangle in, leaving the rest of the UI still.

        ``host`` is the content area (e.g. the page body / its scroll viewport).
        A borderless, topmost Toplevel is placed over exactly that rectangle,
        painted in the page background colour, then its ``-alpha`` eases 1 -> 0.
        The freshly rebuilt content underneath is revealed gradually, while the
        window chrome, navigation and the rest of the background never dim and
        the desktop is never exposed.

        Why a Toplevel: page content lives in ``Canvas.create_window`` child
        windows. Sibling Canvas items / Frames cannot both cover them and let
        them show through (a translucent image over a Canvas item blends with
        that Canvas's own opaque background, not the embedded widgets). Only a
        genuinely transparent top-level overlay can do a local crossfade on
        this Tk build.

        Cleanup is guaranteed on completion, :meth:`cancel`, host destruction
        and errors, so no stray window or leftover alpha is ever left behind.
        """
        if not self.active() or host is None:
            return
        try:
            if not host.winfo_exists() or not host.winfo_viewable():
                return
            host.update_idletasks()
            x = host.winfo_rootx()
            y = host.winfo_rooty()
            w = max(host.winfo_width(), 4)
            h = max(host.winfo_height(), 4)
        except tk.TclError:
            return

        tint = color or T.BG
        try:
            overlay = tk.Toplevel(self.root)
            overlay.overrideredirect(True)
            overlay.attributes("-topmost", True)
            overlay.geometry(f"{w}x{h}+{x}+{y}")
            overlay.configure(bg=tint)
            # overrideredirect() windows only apply geometry after idle tasks,
            # otherwise they stay 1x1 and the fade covers nothing.
            overlay.update_idletasks()
        except tk.TclError:
            return

        self._track_overlay(overlay)

        def clear():
            self._drop_overlay(overlay)

        def frame(t):
            if not overlay.winfo_exists():
                clear()
                return
            try:
                overlay.attributes("-alpha", max(0.0, min(1.0, 1.0 - t)))
            except tk.TclError:
                clear()

        self.tween(duration, frame, clear, easing=easing or ease_in_out)

    def slide_window(self, canvas, item, distance=None, duration=460, direction="left"):
        """Slide a Canvas ``create_window`` item into place horizontally.

        Uses wall-clock time rather than a fixed step count, so a dropped frame
        cannot stretch or stutter the motion. ``distance`` defaults to ~14% of
        the live canvas width (clamped) so the slide reads on any window size.
        The target x is recomputed each frame to survive a mid-flight resize.
        """
        if not self.active() or not canvas.winfo_exists():
            return
        sign = -1 if direction == "left" else 1
        try:
            _bx, base_y = canvas.coords(item)
        except (tk.TclError, ValueError):
            return
        if distance is None:
            width = max(canvas.winfo_width(), 1)
            distance = max(int(width * 0.14), 56)
        distance = int(distance)

        # Snap to the start immediately so there is no "full-size then jump"
        # frame before the first tick.
        def place(progress):
            if not canvas.winfo_exists():
                return
            base = canvas.winfo_width() // 2
            try:
                canvas.coords(item, base + sign * distance * (1 - progress), base_y)
            except tk.TclError:
                pass

        place(0.0)
        start = time.monotonic()

        def step():
            if not canvas.winfo_exists():
                return
            elapsed = (time.monotonic() - start) * 1000.0
            t = min(1.0, elapsed / float(duration))
            place(ease_in_out(t))
            if t < 1.0:
                self.schedule(16, step)
            else:
                place(1.0)

        self.schedule(16, step)
