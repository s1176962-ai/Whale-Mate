"""A self-contained timed player-versus-simulated-AI match."""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from . import modern
from . import skins as skin_store
from . import tokens as T
from .achievement_ui import AchievementToast
from .achievements import AchievementStore
from .augment_ui import AugmentBadge, AugmentCard
from .augments import AugmentRuntime, draw_augments
from .battle import (
    PROFILES,
    ROUND_SECONDS,
    ApiOpponent,
    BattleScore,
    LocalOpponent,
    grade,
    question_seconds,
    speed_bands,
)
from .battle_fx import HealthBar
from .image_cache import portrait_image
from .services import select_questions_weighted
from .widgets import card_frame


class BattlePage:
    @property
    def player_name(self):
        return self.app.user["name"] if self.app.user else "Player"

    @property
    def opponent_name(self):
        return "Big Whale" if self.app.tr.language == "en" else "大肥鱼"

    def __init__(self, app):
        self.app = app
        self.generation = 0
        self.active = False
        self.achievement_toast = AchievementToast(app)
        self._auto_after = None
        self._stage_after = None
        self._best_streak = 0
        self._streak = 0
        self._max_damage = 0
        self._fastest_correct = None
        self.infinite = False
        # Per-round state is reset in round(); declare it here so type checkers
        # see the real types instead of inferring None from the first assignment.
        self.player: BattleScore | None = None
        self.ai: BattleScore | None = None
        self.timer_id: str | None = None
        self.portrait: tk.Label | None = None
        self._portrait_photo: object | None = None

    # Order in which the battle setup fields are presented: question bank,
    # subject, topic, then question count. Remaining knobs follow as "more".
    BANK_PUBLIC = "public"
    BANK_PERSONAL = "personal"
    COUNT_INFINITE = "∞"
    COUNT_OPTIONS = ("3", "5", "10", COUNT_INFINITE)

    def _bank_questions(self):
        """Question pool for the currently selected bank."""
        app = self.app
        if getattr(self, "bank_kind", None) == self.BANK_PERSONAL and app.user:
            return app.personal_questions
        return app.public_questions

    def setup(self):
        from . import modern

        app = self.app
        p = T.palette()
        app._nav_key = "battle"
        app.clear(app.tr("答题对战"), show_heading=False)
        app.load_bank()

        # --- state variables (kept across page rebuilds) -------------------
        bank = getattr(self, "bank_kind", None)
        if bank not in (self.BANK_PUBLIC, self.BANK_PERSONAL):
            bank = self.BANK_PUBLIC
        self.bank_kind = bank
        self.level_labels = {app.tr(level): level for level in PROFILES}
        self.subject = tk.StringVar(
            value=getattr(self, "_subject_value", "All")
        )
        self.topic = tk.StringVar(value=getattr(self, "_topic_value", app.tr("全部")))
        self.count = tk.StringVar(value=getattr(self, "_count_value", "5"))
        self.level = tk.StringVar(value=app.tr("普通级"))
        self.backend = tk.StringVar(
            value="API" if app.ai_settings.load()["api_key"] else "Local"
        )
        self.initial_hp = tk.StringVar(value="100")

        card = modern.SoftCard(app.body)
        card.pack(fill="both", expand=True, pady=(T.px(T.SPACE_2), T.px(T.SPACE_4)))
        self.setup_card = card
        host = card.content

        tk.Label(
            host,
            text=app.tr("双方回答同一道题，每题限时 30 秒；答对后才获得时间分。"),
            bg=p["SURFACE"], fg=p["TEXT_SECONDARY"], font=T.TYPE_CAPTION, anchor="w",
            wraplength=T.px(620), justify="left",
        ).pack(fill="x", pady=(0, T.px(T.SPACE_3)))

        def field(parent, title):
            box = tk.Frame(parent, bg=p["SURFACE"])
            label = tk.Label(
                box, text=title, bg=p["SURFACE"], fg=p["TEXT"],
                font=T.TYPE_BODY, anchor="w", justify="left", wraplength=1,
            )
            # Keep the intrinsic request tiny so uniform grid columns can be
            # sized by the grid, then wrap the heading at the real cell width.
            box.bind(
                "<Configure>",
                lambda event, target=label: target.configure(
                    wraplength=max(1, event.width - T.px(T.SPACE_1))
                ),
                add="+",
            )
            label.pack(fill="x")
            return box

        # The four filters share one CSS-like grid: each column takes an equal
        # share of the card width, so the whole setup stays on one compact row
        # instead of stacking four full-width controls.
        fields = tk.Frame(host, bg=p["SURFACE"])
        fields.pack(fill="x", pady=(0, T.px(T.SPACE_2)))
        gap = T.px(T.SPACE_3)
        for column in range(4):
            fields.columnconfigure(column, weight=1, uniform="battle-setup")
        fields.grid_propagate(True)

        def cell(column):
            return {"row": 0, "column": column, "sticky": "new",
                    "padx": (0, 0) if column == 3 else (0, gap)}

        # 1) Question bank ---------------------------------------------------
        bank_box = field(fields, app.tr("题库"))
        bank_box.grid(**cell(0))
        bank_values = [self.BANK_PUBLIC] + ([self.BANK_PERSONAL] if app.user else [])
        bank_labels = [
            app.tr("公共") if v == self.BANK_PUBLIC else app.tr("我的")
            for v in bank_values
        ]
        self.bank_picker = modern.Segmented(
            bank_box, values=bank_values, labels=bank_labels,
            on_change=self._on_bank_change,
        )
        # Request a tiny intrinsic width; grid's uniform columns distribute the
        # real width, otherwise the canvas' 320px default forces horizontal
        # overflow on a laptop-sized window.
        self.bank_picker.configure(width=1)
        self.bank_picker.set(self.bank_kind)
        self.bank_picker.pack(fill="x", pady=(T.px(T.FIELD_GAP), 0))

        # 2) Subject ---------------------------------------------------------
        subject_box = field(fields, app.tr("科目"))
        subject_box.grid(**cell(1))
        self.subject_box = modern.Dropdown(
            subject_box, textvariable=self.subject, values=[]
        )
        self.subject_box.pack(fill="x", pady=(T.px(T.FIELD_GAP), 0))
        self.subject_box.bind("<<ComboboxSelected>>", self._on_subject_change)

        # 3) Topic -----------------------------------------------------------
        topic_box = field(fields, app.tr("主题"))
        topic_box.grid(**cell(2))
        self.topic_box = modern.Dropdown(
            topic_box, textvariable=self.topic, values=[]
        )
        self.topic_box.pack(fill="x", pady=(T.px(T.FIELD_GAP), 0))
        self.topic_box.bind("<<ComboboxSelected>>", self._remember_filters)

        # 4) Question count (∞ = until someone's HP hits zero) ---------------
        count_box = field(fields, app.tr("题量"))
        count_box.grid(**cell(3))
        count_values = list(self.COUNT_OPTIONS)
        # Keep the row compact: the long infinity label was squeezed into a
        # 4-way segmented control at full width; the hint below explains it.
        count_labels = [str(v) for v in count_values]
        self.count_picker = modern.Segmented(
            count_box, values=count_values, labels=count_labels,
            on_change=self._on_count_change,
        )
        self.count_picker.configure(width=1)
        self.count_picker.set(self.count.get() if self.count.get() in count_values else "5")
        self.count_picker.pack(fill="x", pady=(T.px(T.FIELD_GAP), 0))
        self.count_hint = tk.Label(
            count_box, text="", bg=p["SURFACE"], fg=p["TEXT_MUTED"],
            font=T.TYPE_CAPTION, anchor="w", justify="left", wraplength=1,
        )
        # Start with a tiny request so the uniform grid column can shrink;
        # once the column has its real width, wrap at that width.
        count_box.bind(
            "<Configure>",
            lambda event: self.count_hint.configure(
                wraplength=max(1, event.width - T.px(T.SPACE_1))
            ),
            add="+",
        )
        self.count_hint.pack(fill="x", pady=(T.px(T.SPACE_1), 0))

        # --- More options ---------------------------------------------------
        more = ttk.LabelFrame(host, text=app.tr("更多设置"), padding=T.px(T.SPACE_2))
        more.pack(fill="x", pady=(T.px(T.SPACE_2), 0))
        for column in range(3):
            more.columnconfigure(column, weight=1, uniform="battle-more")
        for column, (label, variable, values) in enumerate((
            ("对手等级", self.level, list(self.level_labels)),
            ("初始血量", self.initial_hp, ["100", "200", "300", "500", "1000"]),
            ("AI", self.backend, ["Local", "API"]),
        )):
            option = ttk.Frame(more)
            option.grid(row=0, column=column, sticky="ew",
                        padx=(0, 0) if column == 2 else (0, gap))
            ttk.Label(option, text=app.tr(label), style="Card.TLabel").pack(anchor="w")
            ttk.Combobox(
                option, textvariable=variable, values=values, state="readonly",
                width=12,
            ).pack(fill="x", pady=(T.px(T.FIELD_GAP), 0))

        # Actions live inside the card. Previously they were packed onto the
        # scroller body *after* an expanding card, which pushed them below the
        # viewport — the reported "missing start button".
        footer = tk.Frame(host, bg=p["SURFACE"])
        footer.pack(side="bottom", fill="x", pady=(T.px(T.SPACE_2), 0))
        actions = tk.Frame(footer, bg=p["SURFACE"])
        actions.pack(side="right")
        self.achievement_button = modern.SoftButton(
            actions, text=app.tr("成就徽章"), variant="secondary",
            command=lambda: app.achievements_page(back=self.setup),
            width=T.px(240),
        )
        self.achievement_button.pack(side="right")
        self.start_button = modern.SoftButton(
            actions, text=app.tr("开始对战"), variant="primary",
            command=self.choose_augment, width=T.px(170),
        )
        self.start_button.pack(side="right", padx=(0, gap))

        self._refresh_battle_subjects()


    def _remember_filters(self, *_args):
        """Persist current filters so a page rebuild restores them."""
        self._subject_value = self.subject.get()
        self._topic_value = self.topic.get()
        self._count_value = self.count.get()

    def _refresh_battle_subjects(self):
        """Rebuild the subject dropdown from the selected bank."""
        pool = self._bank_questions()
        subjects = sorted({q.subject for q in pool})
        if "All" not in subjects:
            subjects = ["All"] + subjects
        self.subject_box.configure(values=subjects)
        if self.subject.get() not in subjects:
            self.subject.set("All")
        self._refresh_battle_topics()

    def _refresh_battle_topics(self):
        """Rebuild topics for the current subject within the selected bank."""
        app = self.app
        pool = self._bank_questions()
        subject = self.subject.get()
        topics = sorted(
            {q.topic for q in pool if subject == "All" or q.subject == subject}
        )
        values = [app.tr("全部")] + topics
        self.topic_box.configure(values=values)
        if self.topic.get() not in values:
            self.topic.set(app.tr("全部"))
        self._remember_filters()
        self._update_count_hint()

    def _on_bank_change(self, value):
        self.bank_kind = value
        self.subject.set("All")
        self.topic.set(self.app.tr("全部"))
        self._refresh_battle_subjects()

    def _on_subject_change(self, *_args):
        self.topic.set(self.app.tr("全部"))
        self._refresh_battle_topics()

    def _on_count_change(self, value):
        self.count.set(value)
        self._remember_filters()
        self._update_count_hint()

    def _update_count_hint(self):
        """Describe how many questions will actually be drawn."""
        hint = getattr(self, "count_hint", None)
        if hint is None or not hint.winfo_exists():
            return
        app = self.app
        if self.count.get() == self.COUNT_INFINITE:
            hint.configure(text=app.tr("无限：打到血量归零"))
            return
        pool = self._bank_questions()
        subject = self.subject.get()
        topic = self.topic.get()
        available = sum(
            (subject == "All" or q.subject == subject)
            and (topic == app.tr("全部") or q.topic == topic)
            for q in pool
        )
        hint.configure(text=app.tr("匹配 {0} 题", available))

    def _prepare_match(self):
        """Validate setup and return (starting HP, selected questions)."""
        app = self.app
        self.difficulty = self.level_labels[self.level.get()]
        maximum = int(self.initial_hp.get())
        if maximum not in (100, 200, 300, 500, 1000):
            raise ValueError(app.tr("请选择有效的初始血量。"))
        subject = None if self.subject.get() == "All" else self.subject.get()
        topic = (
            None
            if self.topic.get() == app.tr("全部")
            else self.topic.get()
        )
        pool = self._bank_questions()
        self.infinite = self.count.get() == self.COUNT_INFINITE
        self._draw_pool = pool
        self._draw_subject = subject
        self._draw_topic = topic
        if self.infinite:
            # Draw every matching question once, ordered by the opponent's
            # difficulty bias. advance() redraws when the deck runs dry.
            matches = [
                q for q in pool
                if (subject is None or q.subject == subject)
                and (topic is None or q.topic == topic)
            ]
            if not matches:
                raise ValueError(app.tr("当前筛选没有匹配的题目。"))
            self._draw_count = len(matches)
        else:
            self._draw_count = int(self.count.get())
        questions = select_questions_weighted(
            pool, self.difficulty, subject, topic, count=self._draw_count
        )
        return maximum, questions

    def choose_augment(self):
        """Show one card per tier before the first round."""
        app = self.app
        try:
            self._prepare_match()
        except ValueError as exc:
            messagebox.showerror(app.tr("无法开始练习"), str(exc), parent=app.root)
            return
        app.clear(app.tr("选择海克斯强化"), show_heading=False, back=self.setup)
        app.label(app.tr("开局四选一，效果持续整场对战。"))
        app.label(app.tr("白银 · 黄金 · 棱彩 · 魔王，每局四档各一张。"))
        self.augment_choices = draw_augments()
        self.augment_cards = []
        for card in self.augment_choices:
            widget = AugmentCard(
                app.body,
                card,
                app.tr,
                command=lambda value=card: self._confirm_augment(value),
                motion=app.motion,
            )
            widget.pack(fill="x", pady=T.px(T.SPACE_2))
            self.augment_cards.append(widget)
        for index, widget in enumerate(self.augment_cards):
            widget.reveal(delay=index * 90)

    def _confirm_augment(self, card):
        self.start(card)

    def start(self, augment=None):
        try:
            maximum, self.questions = self._prepare_match()
        except ValueError as exc:
            messagebox.showerror(self.app.tr("无法开始练习"), str(exc), parent=self.app.root)
            return
        self.selected_augment = augment
        self.difficulty = self.level_labels[self.level.get()]
        self.provider = (
            ApiOpponent(self.app.ai_assistant, self.app.tr.language, self.app.project_root)
            if self.backend.get() == "API"
            else LocalOpponent()
        )
        self.index = 0
        self.records = []
        self.max_hp = maximum
        self.augment = AugmentRuntime(augment, maximum)
        self.player_hp = self.ai_hp = self.max_hp
        self._best_streak = self._streak = self._max_damage = 0
        self._fastest_correct = None
        self.achievement_store = AchievementStore(AchievementStore.path_for(self.app))
        self.round()

    def _cancel_pending(self):
        for key in ("_auto_after", "_stage_after"):
            job = getattr(self, key, None)
            if job is not None:
                try:
                    self.app.root.after_cancel(job)
                except (tk.TclError, ValueError):
                    pass
                setattr(self, key, None)

    def _opponent_deadline(self, question):
        """Opponent window follows the question, never player-side augments."""
        return question_seconds(question.difficulty)

    def _score_opponent(self, question):
        """Score the saved opponent choice against the normal answer window."""
        self.ai = grade(
            self.planned == question.answer,
            self.delay,
            limit=self.ai_grade_limit,
            bands=self.speed_bands,
        )
        self.ai_status.configure(
            text=f"{self.opponent_name}: {self.app.tr('已锁定答案')}"
        )
        self.thinking_status.configure(text=self.app.tr("我选好了，等你一起揭晓。"))

    def round(self):
        app = self.app
        self._cancel_pending()
        self.achievement_toast.dismiss_all()
        self.generation += 1
        generation = self.generation
        app.clear(app.tr("答题对战"), show_heading=False, back=self.leave)
        # Align the question cards with the fixed health bars above and score
        # dock below: all three use SPACE_4 side padding on `outer`. Two traps:
        # (1) the scrollbar narrows `canvas` but not `outer`, so the body must
        # be measured against `outer` (match_outer); (2) the body frame must
        # have ZERO horizontal padding — adding SPACE_4 here on top of the
        # canvas window's SPACE_4 inset shrinks each card another 16px.
        app.set_body_side_pad(T.SPACE_4, match_outer=True)
        app.body.configure(padding=(0, T.px(T.SPACE_1)))
        self.active = True
        self.paused = False
        self._advance_remaining = 3.0
        self.player = self.ai = None
        self.started = time.monotonic()
        q = self.questions[self.index]
        # Difficulty decides the base clock for BOTH sides; augments only
        # touch the player's window so the AI still answers within its profile.
        self.question_limit = question_seconds(q.difficulty)
        self.player_limit = self.augment.limit_for(self.question_limit)
        self.ai_limit = self._opponent_deadline(q)
        self.ai_grade_limit = self.ai_limit
        # Speed-bonus thresholds must match each side's own clock: the player's
        # window may be scaled by an augment, while the AI always uses the
        # base difficulty window. Sharing one band set mis-scores both.
        self.player_speed_bands = speed_bands(self.player_limit)
        self.speed_bands = speed_bands(self.ai_limit)
        self.planned, self.delay = None, self.ai_limit
        self.decision = None
        self.decision_error = None
        responses = queue.Queue()

        def request_opponent():
            try:
                responses.put((self.provider.answer(q, self.difficulty), None))
            except Exception as exc:
                responses.put((None, str(exc)))

        threading.Thread(target=request_opponent, daemon=True).start()
        # Augment banner + health bars live in a fixed strip under the chrome
        # rule. They stay pinned while only the question cards scroll, so the
        # status is always visible and the question gets the whole body.
        header = app._battle_header()
        if self.augment.augment:
            self.augment_badge = AugmentBadge(
                header, self.augment.augment, app.tr, motion=app.motion
            )
            self.augment_badge.pack(fill="x", pady=(0, T.px(2)))
        self.health = ttk.Frame(header)
        self.health.pack(fill="x")
        # Two combatants side by side in one row, as in the reference layout.
        # Equal-weight columns keep both bars the same length and aligned.
        self.health.columnconfigure(0, weight=1, uniform="hp")
        self.health.columnconfigure(1, weight=1, uniform="hp")
        name_font = tkfont.Font(font=T.TYPE_BODY)
        label_width = max(
            name_font.measure(self.player_name),
            name_font.measure(self.opponent_name),
        ) + T.px(8)
        self.player_bar = HealthBar(
            self.health, self.player_name, self.max_hp, motion=app.motion,
            label_width=label_width, height=58,
        )
        self.ai_bar = HealthBar(
            self.health, self.opponent_name, self.max_hp, motion=app.motion,
            label_width=label_width, height=58, mirrored=True,
        )
        self.player_bar.grid(row=0, column=0, sticky="ew", padx=(0, T.px(T.SPACE_2)))
        self.ai_bar.grid(row=0, column=1, sticky="ew", padx=(T.px(T.SPACE_2), 0))
        self.player_bar.set_value(self.player_hp, animate=False)
        self.ai_bar.set_value(self.ai_hp, animate=False)
        scores = ttk.Frame(app.body)
        scores.pack(fill="both", expand=True, pady=T.px(T.SPACE_1))
        for column in (0, 1):
            scores.columnconfigure(column, weight=1, uniform="battle")
        scores.rowconfigure(0, weight=1)
        # The question cards MUST share the health row's exact column geometry:
        # same uniform weight, same symmetric padx. Any asymmetry here (e.g.
        # padx=(0,12) on the left card but (0,0) on the right) shifts the middle
        # gutter off-centre and makes the right card wider than the left, which
        # is exactly the ragged right edge the reference layout forbids.
        player_card = card_frame(scores, pad=T.SPACE_3)
        player_card.grid(row=0, column=0, sticky="nsew", padx=(0, T.px(T.SPACE_2)))
        ai_card = card_frame(scores, pad=T.SPACE_3)
        ai_card.grid(row=0, column=1, sticky="nsew", padx=(T.px(T.SPACE_2), 0))
        self.player_status = ttk.Label(player_card, text=f"{self.player_name}: {app.tr('作答中')}")
        self.player_status.pack(anchor="w")
        self.ai_status = ttk.Label(ai_card, text=f"{self.opponent_name}: {app.tr('阅读题目')}")
        self.ai_status.pack(anchor="w")
        self.portrait = tk.Label(ai_card, bg=T.palette()["SURFACE"], bd=0)
        self.portrait.pack(pady=T.px(T.SPACE_2))
        self.show_expression("thinking")
        from .gui import AssistantReply

        analysis = ttk.Frame(ai_card)
        analysis.pack(fill="both", expand=True, pady=T.px(T.SPACE_2))
        self.thinking_status = AssistantReply(
            analysis,
            text=app.tr("阅读题目"),
            height=5,
            width=1,
            wrap="word",
            bg=T.palette()["SURFACE"],
            fg=T.palette()["TEXT"],
            font=T.TYPE_BODY,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        scroll = ttk.Scrollbar(analysis, orient="vertical", command=self.thinking_status.yview)
        scroll.pack(side="right", fill="y")
        self.thinking_status.configure(yscrollcommand=scroll.set)
        self.thinking_status.pack(side="left", fill="both", expand=True)
        self.current_stage = -1
        self.show_decision_stage(0)
        ttk.Label(player_card, text=q.question, wraplength=T.px(420), style="Question.TLabel").pack(
            fill="x", pady=T.px(T.SPACE_3)
        )
        app.show_image(q.question_image, parent=player_card, max_width=160)
        hidden = self.augment.hidden_option_index(q.options, q.answer)
        self.buttons = []
        for index, option in enumerate(q.options):
            button = modern.SoftButton(
                player_card,
                text=f"{chr(65 + index)}  {option}",
                command=lambda value=option: self.answer(value),
                variant="secondary",
            )
            button.pack(fill="x", pady=T.px(2))
            if index == hidden:
                button.configure(text=app.tr("洞察已排除"))
                button.state(["disabled"])
            if index != hidden and q.option_images and q.option_images[index]:
                app.show_image(q.option_images[index], parent=player_card, max_width=180)
            self.buttons.append(button)
        dock = app._action_dock()
        from .battle_result import ScoreCard

        # Symmetric, self-sizing grid (the Tk equivalent of CSS grid):
        #   col 0 = player card (fixed) | col 1 = centre (flexes) | col 2 = AI card (fixed)
        #   row 0 = round clock         | row 1 = battle-data output (moved down)
        # The two score cards share ONE uniform column definition, so they stay
        # mirror-symmetric at any window size — no hand-counted pixel widths.
        # The centre column flexes (weight=1) like `flex: 1` in HTML.
        panel = card_frame(dock, pad=T.SPACE_3)
        panel.pack(fill="x", pady=(0, T.px(2)))
        panel.columnconfigure(0, weight=0, uniform="score")
        panel.columnconfigure(1, weight=1, minsize=T.px(240))
        panel.columnconfigure(2, weight=0, uniform="score")

        accent_player = T.palette().get("PRIMARY")
        self.player_score = ScoreCard(
            panel, self.player_name, app.tr, accent=accent_player, motion=app.motion,
            height=58,
        )
        self.player_score.grid(
            row=0, column=0, rowspan=2, sticky="nsw", padx=(0, T.px(T.SPACE_2))
        )
        self.ai_score = ScoreCard(
            panel, self.opponent_name, app.tr, accent="#EF4444", motion=app.motion,
            height=58, mirrored=True,
        )
        self.ai_score.grid(
            row=0, column=2, rowspan=2, sticky="nse", padx=(T.px(T.SPACE_2), 0)
        )

        # Clock leads the centre column; the battle-data output sits on the
        # row BELOW it so the answer text is never sandwiched between the two
        # score cards' number boxes (that crowding read as "content covered").
        self.clock = ttk.Label(
            panel,
            text=f"{self.index + 1} / {len(self.questions)} · {self.player_limit}s",
            style="Question.TLabel", anchor="center", justify="center",
        )
        self.clock.grid(row=0, column=1, sticky="n")
        data_row = ttk.Frame(panel)
        data_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(T.px(8), 0))
        result_frame = ttk.Frame(data_row)
        result_frame.pack(fill="x")
        self.result = AssistantReply(
            result_frame,
            text="",
            height=2,
            width=1,
            wrap="word",
            justify="center",
            bg=T.palette()["SURFACE"],
            fg=T.palette()["TEXT"],
            font=T.TYPE_CAPTION,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        result_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.result.yview)

        def sync_scroll(first, last):
            result_scroll.set(first, last)
            if float(first) > 0.001 or float(last) < 0.999:
                if not result_scroll.winfo_manager():
                    result_scroll.pack(side="right", fill="y")
            else:
                result_scroll.pack_forget()

        self.result.configure(yscrollcommand=sync_scroll)
        self.result.pack(side="left", fill="x", expand=True)

        def fit_result(_event=None):
            lines = self.result.count("1.0", "end-1c", "displaylines")
            height = min(4, max(2, (lines[0] if lines else 0) + 1))
            if int(self.result.cget("height")) != height:
                self.result.configure(height=height)

        self.result.bind("<Configure>", fit_result)
        self.fit_result = fit_result
        palette = T.palette()
        control_style = ttk.Style(app.root)
        control_style.layout("BattlePlayback.TButton", [
            ("Button.padding", {"sticky": "nswe", "children": [
                ("Button.label", {"sticky": "nswe"}),
            ]}),
        ])
        control_style.configure(
            "BattlePlayback.TButton", background=palette["SURFACE"],
            foreground=palette["TEXT_SECONDARY"], padding=(T.px(4), T.px(2)),
            font=T.TYPE_BODY, anchor="center", relief="flat", borderwidth=0,
        )
        control_style.map(
            "BattlePlayback.TButton",
            background=[("disabled", palette["SURFACE"]),
                        ("pressed", palette["RAISED"]),
                        ("active", palette["RAISED"]),
                        ("focus", palette["RAISED"])],
            foreground=[("disabled", palette["TEXT_MUTED"]),
                        ("active", palette["TEXT"])],
        )
        self.next = ttk.Button(
            panel, text="⏸", width=3, command=self.toggle_pause, style="BattlePlayback.TButton"
        )
        self.next.grid(row=1, column=1, pady=(T.px(4), 0))
        self.next.state(["disabled"])
        # Bind the button too: stop its native Space handler from invoking it
        # again before the event reaches the root binding.
        def space(event):
            if isinstance(event.widget, (tk.Entry, ttk.Entry)):
                return
            self.toggle_pause()
            return "break"

        key_id = app.root.bind("<space>", space, add="+")
        self.next.bind("<space>", space)

        def cleanup_control(event):
            if event.widget is self.next:
                app.root.unbind("<space>", key_id)
                self._cancel_pending()

        self.next.bind("<Destroy>", cleanup_control)

        def tick():
            if generation != self.generation or not self.active or not self.clock.winfo_exists():
                return
            elapsed = time.monotonic() - self.started
            try:
                response, error = responses.get_nowait()
                self.receive_decision(response, error, elapsed, self.ai_limit)
            except queue.Empty:
                pass
            if self.ai is None:
                _, low, high = PROFILES[self.difficulty]
                duration = self.delay if self.decision else (low + high) / 2
                stage = min(2, int(elapsed / max(duration, 1) * 3))
                self.show_decision_stage(stage)
            clock_text = (
                f"{self.index + 1} / {len(self.questions)} · "
                f"{max(0, self.player_limit - int(elapsed))}s"
            )
            if self.clock.cget("text") != clock_text:
                self.clock.configure(text=clock_text)
            if self.ai is None and self.planned is not None and elapsed >= self.delay:
                self._score_opponent(q)
            if self.ai is None and elapsed >= self.ai_limit:
                if self.decision is None:
                    self.decision_error = app.tr("等待对手决策超时。")
                self.ai = grade(False, self.ai_limit + 1, limit=self.ai_grade_limit)
            if self.player is None and elapsed >= self.player_limit:
                self.answer(None, timed_out=True, limit=self.player_limit)
            if self.player is not None and self.ai is not None:
                self.finish_round()
                return
            self.timer_id = app.root.after(100, tick)

        tick()

    def receive_decision(self, response, error, elapsed, decision_limit=None):
        """Reject late responses before assigning an answer or scoring it."""
        decision_limit = (
            getattr(self, "ai_limit", ROUND_SECONDS)
            if decision_limit is None else decision_limit
        )
        if error or elapsed >= decision_limit:
            self.decision = None
            self.planned = None
            self.decision_error = error or self.app.tr("等待对手决策超时。")
            self.ai = grade(False, decision_limit + 1, limit=self.ai_grade_limit)
            self.ai_status.configure(text=self.app.tr("AI 服务不可用，本题未作答"))
            return
        self.decision = response
        self.planned, self.delay = response
        self.delay = max(self.delay, elapsed)

    def answer(self, value, timed_out=False, limit=None):
        if self.player is not None:
            return
        limit = getattr(self, "player_limit", ROUND_SECONDS) if limit is None else limit
        elapsed = limit + 1 if timed_out else time.monotonic() - self.started
        self._last_elapsed = elapsed
        # player_score() mutates match-long augment state (streak). Save a
        # snapshot so a voided round can roll it back before the retry.
        self._augment_snapshot = self.augment.checkpoint()
        self.player = self.augment.player_score(
            value == self.questions[self.index].answer,
            elapsed,
            player_hp=self.player_hp,
            limit=limit,
            bands=getattr(self, "player_speed_bands", None),
        )
        for button in self.buttons:
            button.state(["disabled"])
        self.player_status.configure(text=f"{self.player_name}: {self.app.tr('已锁定答案')}")

    def finish_round(self):
        if not self.active:
            return
        self.active = False
        if self.decision_error:
            # The round is voided (no score / no HP loss); roll back any
            # match-long augment state mutated by answer(), so retrying the
            # same question cannot jump a streak tier (e.g. +20 -> +40).
            snapshot = getattr(self, "_augment_snapshot", None)
            if snapshot is not None:
                self.augment.restore(snapshot)
            self.ai_status.configure(
                text=self.app.tr("对手作答异常"), foreground=T.palette()["TEXT"]
            )
            self.show_expression("thinking")
            self.thinking_status.configure(
                text=self.app.tr("对手未返回有效答案，本题作废，不计分也不扣血。")
                + "\n\n"
                + self.app.tr("异常原因：")
                + self.decision_error
            )
            self.result.configure(text=self.app.tr("本题未结算，请重试。"))
            self.player_score.clear()
            self.ai_score.clear()
            self.paused = True
            self.next.configure(text="▶")
            self.next.state(["!disabled"])
            self.fit_result()
            return
        # tick() only calls us once both sides have scored, so these are set.
        player, ai = self.player, self.ai
        assert player is not None and ai is not None
        q = self.questions[self.index]
        letter = chr(65 + q.options.index(self.planned)) if self.planned in q.options else "—"
        self.ai_status.configure(
            text=f"{self.opponent_name}: {letter}",
            foreground="#22C55E" if ai.correct else "#EF4444",
            font=T.TYPE_HEADING,
        )
        self.show_expression("correct" if ai.correct else "wrong")
        self.thinking_status.configure(
            text=self.app.tr("回答正确") if ai.correct else self.app.tr("再想一想")
        )
        self.records.append((player, ai))
        previous_player_hp, previous_ai_hp = self.player_hp, self.ai_hp
        self.player_hp, self.ai_hp, augment_notes = self.augment.damage(
            self.player_hp,
            self.ai_hp,
            player,
            ai,
            player_correct=bool(player.correct),
            ai_correct=bool(ai.correct),
        )
        player_damage = previous_player_hp - self.player_hp
        ai_damage = previous_ai_hp - self.ai_hp
        self._max_damage = max(self._max_damage, ai_damage)
        if player.correct:
            self._streak += 1
            self._best_streak = max(self._best_streak, self._streak)
            # Use this round's real player window: a hard question (45s) or a
            # timing augment (sandglass +8s / demon pact halved) makes the old
            # fixed 30s cut-off silently drop valid fast answers.
            elapsed = getattr(self, "_last_elapsed", self.player_limit + 1)
            if elapsed <= self.player_limit and (
                self._fastest_correct is None or elapsed < self._fastest_correct
            ):
                self._fastest_correct = elapsed
        else:
            self._streak = 0
        self._stage_damage(player_damage, ai_damage)
        chosen = self.planned
        record = self.app.tr(
            "本题 {0} · 我的选择：{1} · 正确答案：{2}", q.id, chosen or "—", q.answer
        )
        stage_titles = ("读题", "分析选项", "选择并检查")
        process = "\n\n".join(
            f"{index + 1}. {self.app.tr(title)}\n{summary}"
            for index, (title, summary) in enumerate(
                zip(stage_titles, self.decision.stages if self.decision else ())
            )
        )
        basis = (
            self.decision.basis
            if self.decision and self.decision.source == "api"
            else self.app.tr("这是按等级概率产生的模拟选择，不是模型解题决策。")
            if self.decision
            else self.app.tr("本题没有有效决策记录。")
        )
        explanation = (
            process
            + "\n\n"
            + record
            + "\n\n"
            + self.app.tr("作答时的决策依据：")
            + "\n"
            + basis
            + "\n\n"
            + self.app.tr("题库解析：")
            + "\n"
            + q.explanation
        )
        self.thinking_status.configure(text=explanation)
        # Score breakdown lives in the side cards now; the centre dialog shows
        # the answer, explanation and augment notes only.
        result_text = f"{self.app.tr('正确答案')}：{q.answer}\n{q.explanation}"
        if augment_notes:
            result_text += "\n" + " ".join(self.app.tr(note) for note in augment_notes)
        self.result.configure(text=result_text)
        # Feed the segmented score cards; the centre dialog keeps the full text.
        self.player_score.set_score(player)
        self.ai_score.set_score(ai)
        self.next.state(["!disabled"])
        self.paused = not bool(player.correct)
        self.next.configure(text="▶" if self.paused else "⏸")
        self.fit_result()
        if not self.paused:
            self._schedule_auto_advance()

    def _stage_damage(self, player_damage, ai_damage):
        """Play the hit pose and animate the bars that actually lost HP."""
        if self.ai_hp <= 0:
            self.show_expression("die")
        elif ai_damage > 0:
            self.show_expression("attacked")
            self.ai_bar.flash()
        elif player_damage > 0:
            self.show_expression("attack")
            self.player_bar.flash()
        self.player_bar.set_value(self.player_hp)
        self.ai_bar.set_value(self.ai_hp)
        for bar, damage in ((self.player_bar, player_damage), (self.ai_bar, ai_damage)):
            if damage > 0:
                bar.float_text(f"−{damage}")
        # Demon pact: make the 3x hit unmistakable with a floating badge.
        if self.augment.id == "demon_pact" and ai_damage > 0:
            self.ai_bar.float_text("×3", color="#FF2D37")
            if self.app.motion and self.app.motion.active():
                self.app.motion.schedule(
                    110, lambda: self.ai_bar.float_text("×3", color="#FFFFFF")
                )

    def toggle_pause(self):
        """Pause result review only; the answer clock must always keep running."""
        if self.active or not self.next.winfo_exists():
            return
        if self.decision_error:
            self.round()
            return
        if self.paused:
            self.paused = False
            self.next.configure(text="⏸")
            self._schedule_auto_advance()
        else:
            self._advance_remaining = max(0.1, self._advance_deadline - time.monotonic())
            self._cancel_pending()
            self.paused = True
            self.next.configure(text="▶")

    def _schedule_auto_advance(self):
        """Resume the result countdown with its remaining review time."""
        self._cancel_pending()
        generation = self.generation
        self._advance_deadline = time.monotonic() + self._advance_remaining

        def advance():
            self._auto_after = None
            if generation != self.generation or self.paused:
                return
            self.advance()

        self._auto_after = self.app.root.after(
            max(1, int(self._advance_remaining * 1000)), advance
        )

    def show_decision_stage(self, stage):
        """Replace the previous activity; never expose an opponent answer early."""
        if self.current_stage == stage:
            return
        self.current_stage = stage
        messages = (
            "先读题，看看它问的是什么……",
            "再看看各个选项，比较它们与题意是否相符……",
            "选一个答案，再检查有没有漏掉条件……",
        )
        self.thinking_status.configure(text=f"{stage + 1} / 3\n\n{self.app.tr(messages[stage])}")

    @property
    def _skin_id(self):
        """Active portrait skin id.

        A manual selection in Settings overrides the difficulty rule; the
        default ``auto`` keeps following the difficulty (hell -> hell pack).
        """
        root = self.app.project_root
        difficulty = getattr(self, "difficulty", None)
        prefs = getattr(self.app, "skin_prefs", None)
        chosen = (
            prefs.selected(root, "battle", difficulty)
            if prefs is not None
            else skin_store.AUTO_SKIN
        )
        return skin_store.resolve_battle_skin(root, difficulty, chosen)

    @property
    def _hell_art(self):
        """True when the active skin is the hell (black/red gothic) pack."""
        return self._skin_id == "hell"

    def _portrait_source(self, state):
        """Return (path, is_sheet) for a portrait state from the active skin.

        Portraits come from swappable skin packs under ``assets/battle/skins``.
        Hell difficulty selects the ``hell`` skin (7 standalone poses incl. the
        idle/anger ``normal`` and the correct/wrong reactions); every other
        difficulty uses ``default``. The skin store resolves missing files back
        through the default pack and legacy flat assets, so no state can ever
        render a blank portrait.
        """
        root = self.app.project_root
        path = skin_store.portrait_path(root, self._skin_id, state)
        if path is None:
            path = root / "AI-assistant-icon.png"
        return path, skin_store.is_sheet(root, self._skin_id, state)

    def show_expression(self, state):
        app = self.app
        portrait = self.portrait
        if portrait is None:
            return
        path, is_sheet = self._portrait_source(state)
        if not path.exists():
            path = app.project_root / "AI-assistant-icon.png"
            is_sheet = False
        try:
            self._portrait_photo = portrait_image(
                app.root, path, state, T.px(160), sheet=is_sheet
            )
            portrait.configure(image=self._portrait_photo)
        except (tk.TclError, OSError):
            portrait.configure(text="AI")

    def advance(self):
        self._cancel_pending()
        self.index += 1
        alive = self.player_hp > 0 and self.ai_hp > 0
        if alive and self.index >= len(self.questions):
            # Infinite mode: reshuffle the deck and keep going until a side's
            # HP is depleted. Finite mode falls through to the results page.
            if getattr(self, "infinite", False) and self.questions:
                self.questions = select_questions_weighted(
                    self._draw_pool, self.difficulty,
                    self._draw_subject, self._draw_topic,
                    count=self._draw_count,
                )
                self.index = 0
            else:
                alive = False
        if alive and self.index < len(self.questions):
            self.round()
            return
        app = self.app
        won = self.player_hp > self.ai_hp
        # Badges earned this battle; shown on the result page below the score.
        # Initialised up front so the result render can always read it.
        unlocked = []
        # Badges are bound to a real account; guests never persist progress.
        if app.user:
            try:
                unlocked = self.achievement_store.evaluate(
                    {
                        "finished": True,
                        "won": won,
                        "max_hp": self.max_hp,
                        "difficulty": self.difficulty,
                        "player_hp": self.player_hp,
                        "ai_hp": self.ai_hp,
                        "augment_rarity": self.augment.augment.rarity
                        if self.augment.augment
                        else None,
                        "best_streak": self._best_streak,
                        "max_single_damage": self._max_damage,
                        "fastest_correct": self._fastest_correct,
                    }
                )
                if unlocked:
                    self.achievement_toast.show(unlocked)
            except (ValueError, OSError):
                pass
        app.clear(app.tr("对战结果"), show_heading=False, back=self.setup)
        player = sum(pair[0].total for pair in self.records)
        ai = sum(pair[1].total for pair in self.records)
        app.label(
            app.tr("胜利")
            if self.player_hp > self.ai_hp
            else app.tr("平局")
            if self.player_hp == self.ai_hp
            else app.tr("惜败"),
            "Question.TLabel",
        )
        app.label(f"{self.player_name} {player} : {ai} {self.opponent_name}")
        app.label(f"HP {self.player_hp} : {self.ai_hp}")
        if self.augment.augment:
            AugmentBadge(
                app.body, self.augment.augment, app.tr, motion=app.motion
            ).pack(fill="x", pady=T.px(T.SPACE_1))

        # Show the badges completed in this battle using the very same cards as
        # the achievement wall, so the result page doubles as a reward recap.
        if unlocked:
            from .achievement_ui import AchievementCard

            app.label(app.tr("本局解锁的成就"), "Question.TLabel")
            grid = ttk.Frame(app.body)
            grid.pack(fill="x", pady=T.px(T.SPACE_1))
            for index, badge in enumerate(unlocked):
                card = AchievementCard(
                    grid, badge, True, app.tr, motion=app.motion
                )
                card.grid(
                    row=index // 2, column=index % 2,
                    sticky="nsew", padx=T.px(T.SPACE_1), pady=T.px(T.SPACE_1),
                )
            for column in (0, 1):
                grid.columnconfigure(column, weight=1, uniform="result-badge")

        app.button(app.tr("再战一次"), self.setup, "Accent.TButton")

    def leave(self):
        if self.active and not messagebox.askyesno(
            self.app.tr("答题对战"), self.app.tr("退出当前对战？"), parent=self.app.root
        ):
            return
        self.active = False
        self.generation += 1
        self._cancel_pending()
        self.achievement_toast.dismiss_all()
        self.setup()
