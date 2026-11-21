"""Live showcase of the three micro-interactions added to WhaleMate.

Run it from the project root::

    .venv/Scripts/python.exe examples/motion_demo.py

It uses the app's real design tokens, Motion engine and Canvas widgets, so the
effects are identical to what you see in the full application. Nothing here
writes to the user's profile or data directory.
"""

import sys
import tempfile
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from learning_platform import modern
from learning_platform import ui_tokens as T
from learning_platform.mascot import MascotWalker
from learning_platform.motion import Motion


def main():
    tmp = tempfile.TemporaryDirectory()
    root = tk.Tk()
    root.tk.call("tk", "scaling", "1.333")
    root.title("WhaleMate · 微交互演示")
    root.configure(bg=T.BG)
    root.resizable(False, False)

    motion = Motion(root)
    modern.set_motion(motion)
    T.set_theme("light")
    root.configure(bg=T.BG)

    wrap = tk.Frame(root, bg=T.BG, padx=32, pady=26)
    wrap.pack(fill="both", expand=True)

    title = tk.Label(
        wrap,
        text="微交互演示",
        font=T.TYPE_TITLE,
        fg=T.TEXT,
        bg=T.BG,
        anchor="w",
    )
    title.pack(fill="x", pady=(0, 4))
    sub = tk.Label(
        wrap,
        text="把鼠标移到按钮或导航上 · 点击按钮切换页面 · 点击看页面渐入 · 切换主题看颜色过渡",
        font=T.TYPE_CAPTION,
        fg=T.TEXT_SECONDARY,
        bg=T.BG,
        anchor="w",
        justify="left",
    )
    sub.pack(fill="x", pady=(0, 20))

    # --- 1. Button colour fade (hover / press) -----------------------------
    sec1 = tk.LabelFrame(
        wrap, text="  1 · 按钮渐变（悬停 / 按下）  ", font=T.TYPE_HEADING,
        fg=T.TEXT, bg=T.BG, bd=1, relief="groove", padx=16, pady=14,
    )
    sec1.pack(fill="x", pady=(0, 14))
    row = tk.Frame(sec1, bg=T.BG)
    row.pack(fill="x")
    modern.SoftButton(row, text="主要按钮", variant="primary", width=150).pack(
        side="left", padx=(0, 12)
    )
    modern.SoftButton(row, text="幽灵按钮", variant="ghost", width=150).pack(
        side="left", padx=(0, 12)
    )
    modern.SoftButton(row, text="描边按钮", variant="outline", width=150).pack(side="left")
    hint = tk.Label(
        sec1,
        text="颜色在 140ms 内平滑过渡，按下时再深一档——用 after() 逐帧 T.mix，不依赖 Qt。",
        font=T.TYPE_CAPTION, fg=T.TEXT_MUTED, bg=T.BG, anchor="w", justify="left",
    )
    hint.pack(fill="x", pady=(12, 0))

    # --- 2. Soft page fade-in ---------------------------------------------
    sec2 = tk.LabelFrame(
        wrap, text="  2 · 页面渐入  ", font=T.TYPE_HEADING,
        fg=T.TEXT, bg=T.BG, bd=1, relief="groove", padx=16, pady=14,
    )
    sec2.pack(fill="x", pady=(0, 14))
    stage = tk.Frame(sec2, bg=T.PRIMARY_SOFT, height=96)
    stage.pack(fill="x")
    stage.pack_propagate(False)
    stage.update_idletasks()

    fade_host = tk.Frame(stage, bg=T.PRIMARY_SOFT)
    fade_host.place(relx=0, rely=0, relwidth=1, relheight=1)
    card = modern.SoftCard(fade_host, padding=14, shadow=True)
    card.place(relx=0.5, rely=0.5, anchor="center")
    card_label = tk.Label(
        card.content, text="内容面板", font=T.TYPE_BODY_LARGE, fg=T.TEXT, bg=T.SURFACE
    )
    card_label.pack()

    def do_fade():
        motion.fade_overlay(fade_host, duration=560, color=T.PRIMARY_SOFT)

    modern.SoftButton(
        sec2, text="▶  重播渐入", variant="primary", width=150, command=do_fade
    ).pack(anchor="w", pady=(12, 0))

    # --- 3. Theme colour transition ---------------------------------------
    sec3 = tk.LabelFrame(
        wrap, text="  3 · 颜色过渡（主题切换）  ", font=T.TYPE_HEADING,
        fg=T.TEXT, bg=T.BG, bd=1, relief="groove", padx=16, pady=14,
    )
    sec3.pack(fill="x")

    def toggle_theme():
        nxt = "dark" if T.theme_name() == "light" else "light"
        old = T.BG
        T.set_theme(nxt)
        for w in (root, wrap, title, sub, sec1, sec2, sec3, sec4, row, hint, stage, fade_host, ctl, mnote):
            try:
                w.configure(bg=T.BG)
            except tk.TclError:
                pass
        pond.configure(bg=T.AI_REPLY_BG)
        theme_btn.configure(text=f"切换到{'浅色' if nxt == 'dark' else '深色'}模式")
        motion.color_wash(wrap, old, T.BG, duration=420)

    theme_btn = modern.SoftButton(
        sec3, text="切换到深色模式", variant="outline", width=180, command=toggle_theme
    )
    theme_btn.pack(side="left")
    tnote = tk.Label(
        sec3,
        text="整屏颜色在 420ms 内由旧配色渐变到新配色。",
        font=T.TYPE_CAPTION, fg=T.TEXT_MUTED, bg=T.BG, anchor="w",
    )
    tnote.pack(side="left", padx=(16, 0))

    # --- 4. Assistant mascot pacing --------------------------------------
    sec4 = tk.LabelFrame(
        wrap, text="  4 · 吉祥物走动 + 催学气泡（AI 助手）  ", font=T.TYPE_HEADING,
        fg=T.TEXT, bg=T.BG, bd=1, relief="groove", padx=16, pady=14,
    )
    sec4.pack(fill="x", pady=(14, 0))
    pond = tk.Canvas(sec4, height=196, bg=T.AI_REPLY_BG, highlightthickness=0, bd=0)
    pond.pack(fill="x")
    walker = MascotWalker(
        pond, ROOT / "AI-assistant-icon.png", motion=motion,
        travel=0.40, speed=0.7, bob=5.0, top_pad=T.px(48), language="zh",
    )

    def toggle_walk():
        if walker._job is None:
            walker.start()
            walk_btn.configure(text="⏸  暂停走动")
        else:
            walker.stop()
            walk_btn.configure(text="▶  继续走动")

    def toggle_lang():
        nxt = "en" if walker.language == "zh" else "zh"
        walker.set_language(nxt)
        lang_btn.configure(text="语言：EN" if nxt == "en" else "语言：中文")

    ctl = tk.Frame(sec4, bg=T.BG)
    ctl.pack(anchor="w", pady=(12, 0))
    walk_btn = modern.SoftButton(
        ctl, text="⏸  暂停走动", variant="outline", width=140, command=toggle_walk
    )
    walk_btn.pack(side="left")
    lang_btn = modern.SoftButton(
        ctl, text="语言：中文", variant="outline", width=110, command=toggle_lang
    )
    lang_btn.pack(side="left", padx=(10, 0))
    mnote = tk.Label(
        sec4,
        text="吉祥物在框内来回踱步并弹出催学气泡 · 中英文随时切换 · 首页会低频调用 AI 生成新台词（无 Key 时用内置短句）",
        font=T.TYPE_CAPTION, fg=T.TEXT_MUTED, bg=T.BG, anchor="w", justify="left",
    )
    mnote.pack(fill="x", pady=(8, 0))

    note = tk.Label(
        wrap,
        text="提示：在「设置 → 动效」里关闭后，以上所有过渡都会立即完成，不会有等待。",
        font=T.TYPE_CAPTION, fg=T.TEXT_MUTED, bg=T.BG, anchor="w", justify="left",
    )
    note.pack(fill="x", pady=(18, 0))

    def on_close():
        walker.stop()
        motion.cancel()
        tmp.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.eval("tk::PlaceWindow . center")
    root.after(300, pond.update_idletasks)
    root.after(400, walker.start)  # set the mascot pacing on launch
    root.after(400, do_fade)  # show the fade-in once on launch
    root.mainloop()


if __name__ == "__main__":
    main()
