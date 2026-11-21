# 变更记录

## 魔王保底与演示抽卡 · 2026-11-21

- 普通抽卡连续三次未出现魔王后，第四次必含魔王；出现即重置。按实际打开抽卡页的发牌次数计算，不要求选中魔王；按账号持久化，访客进度单独保存。
- 对战设置新增“演示抽卡：魔王必出”，重新进入设置默认关闭；演示抽卡不读写普通保底进度，仍为三张不同卡牌。
- 抽卡页显示保底剩余次数或演示标记；本机访客保底存档加入 Git 忽略规则。

## 无限模式主动结算与暂停提示 · 2026-11-21

- 无限对战揭晓后提供“结束并结算”，作答期间禁用；主动结束只汇总已结算回合，不计胜负/完成场次或通关成就，单题/连击成就可保存。血量归零仍正常结算，取消自动推进并防止重复结算。
- 暂停按钮旁说明作答、等待、自动推进、答错暂停、手动暂停和异常重试状态，提示空格操作；无限模式题号跨牌堆累计。
- BATTLE.md 重整为双语当前规则，旧迭代归档；README、specification、SRS 与索引同步，移除固定 30 秒、四选一、三倍伤害及手动继续等旧规则混用。

## 海克斯随机三选一 · 2026-11-21

- 取消四选一及固定每档一张，改用卡牌已有权重，从全池不放回抽三张。每手卡牌不重复，允许同稀有度多张，不保证出现魔王。
- 同步中英文提示与规则文档，回归覆盖数量、重复、稀有度变化及权重。

## 开启动画时 Settings / Notebook 滚动修复 · 2026-11-21

- 根因：页面渐入动画提前刷新空容器布局，使滚动主体固定为视口高度；新内容增长后主体尺寸不变，原来的 Configure 监听无法更新滚动范围。
- 页面重建后在空闲阶段重新测量内容，并合并主体内子控件的布局变化，更新主体高度和滚动区域；保留短页铺满视口的行为。关闭窗口时取消待处理的布局回调。
- 回归覆盖开启动画、固定窗口尺寸下 Settings → Notebook → History → Settings 的切换、滚轮滚动和底部可达性。

## 审查问题修复 · 2026-11-21

- 动画管理器跟踪全部活动遮罩；取消动画时统一销毁，避免并发动画留下遮挡层。单个动画完成仅清理自己的遮罩。
- 对战皮肤选择、难度默认值及立绘加载优先使用统一皮肤注册表；缺图回退默认皮肤，保留旧注册表兼容。
- 海克斯奖励与连击使用时限校验后的正确状态；超时点击正确选项不加分，并打断连击。
- 新增遮罩并发取消、统一注册表自定义皮肤端到端加载、旧注册表兼容及超时计分回归测试。

## 尊重题库删题 + 测试去 ID 硬编码 · 2026-11-20

- 撤回上一轮误操作：ENG001（英文题配中文选项）与 MAT012（分数用 `3/4`、`15/8` 纯文本展示）是用户有意删除的展示问题题，不应从版本库恢复；题库恢复为 19 + 19 + 20 = 58 题。
- `tests/test_core.py` 不再写死 60 题，改为断言 58 题与「答案必在选项内」不变量；`test_personal_and_plan.py` 的公共题冲突样例从 ENG001 换成仍在库的 ENG002。
- `tests/test_roles_and_language.py` 与 `docs/DESIGN.md` 删除对已不存在题目的具体引用，改为通用表述；旧条目里「恢复误删 MAT012」的说明同步标注为已撤回。

## 难度加权抽题 + 分难度计时 + 魔王效果重做 · 2026-11-20

- **按对手难度加权抽题**：`services.select_questions_weighted()` 按 easy/medium/hard 桶权重抽题，推荐梯度入门 70/25/5、普通 40/45/15、困难 15/45/40、地狱 5/25/70；缺桶时权重重新分配，不放回抽取。`battle_ui._prepare_match()` / ∞ 模式重洗统一改走该函数，普通练习页仍用原来的精确筛选。
- **题目难度决定时间**：`battle.py` 新增 `QUESTION_SECONDS`（easy 25s / medium 30s / hard 45s）与 `speed_bands()`；速度分阈值按比例缩放（25s→4/8/12/17/25，45s→8/15/23/30/45）。`grade(..., bands=...)` 兼容旧调用；双方计时都按题目难度取窗口，海克斯只作用玩家侧。
- **魔王契约重做**：`AugmentRuntime.limit_for(base)` 取代固定 7 秒，魔王玩家时间 = 本题 base 的 50%；`player_score()` 把本题总得分整体 ×3（100+50→450），原「造成伤害 ×3」特殊逻辑移除，伤害回归分差自然结算。卡牌描述、结算提示、英文文案同步更新；飘字「×3」保留但含义改为得分。
- 测试：新增/更新加权分布、分难度时钟与速度分、魔王 50%/总分×3 的规则与 GUI 回归；全套 unittest 通过。BATTLE.md 同步。

## 对战设置页紧凑单行布局 + 恢复开始按钮 · 2026-11-20

- 用户反馈设置页四个筛选项（题库/科目/主题/题量）各占满一整行，占篇幅过大，且「开始对战」按钮不见。
- `BattlePage.setup()` 把四个筛选项改成 4 列 `uniform` grid，统一同一行、等宽并顶部对齐；「更多设置」的对手等级/初始血量/AI 也改为 3 列同行。Segmented/Canvas 初始请求宽度设为 1，标题与题量提示按单元格实际宽度动态换行，避免窄窗口横向溢出。
- 根因：按钮原先 `app.button()` 挂在滚动 body 上、排在 `expand=True` 的 SoftCard 之后，被挤出视口。现在「开始对战」/「成就」放在卡片内部底部操作条，`start_button` / `achievement_button` 可回归测试。
- 题量标签精简为 `3 / 5 / 10 / ∞`，说明文字缩短为「匹配 N 题 / ∞：打到血量归零」；题库分段标签精简（公共 / Mine）；去掉冗余规则长文案。`modern.Segmented._draw()` 增加按段宽测量并自动降字号/省略号，防止窄列内文字重叠。
- 新增英文文案（Public/Mine/我的、短题量提示、短规则说明）；新增回归测试 `test_battle_setup_filters_share_one_row_and_actions_stay_in_card` 校验同行列号与按钮归属。全套测试与语法检查通过。

## 结算页成就 + 成就换行 + 对战设置重排 + 组件失效修复 + 重置成就 · 2026-11-20

- **结算页展示本局成就**：`BattlePage.advance()` 把 `unlocked` 提前初始化，结算页在分割比分/海克斯卡下方用与成就墙相同的 `AchievementCard` 两列网格列出本局新解锁的徽章（标题「本局解锁的成就」）；访客不落盘则为空。新增英文文案。
- **成就描述换行修复**：`achievement_ui._wrap()` 原来按 24 字符硬切且只取两行，英文单词被从中间劈开（Hell-di/fficulty、corre/ctly）。改为 `_wrap_pixels()`：用 Tk `font measure` 按像素宽、按空格分词换行，长单词/中文再逐字兜底，最多 3 行；卡片高度 116→132。验证所有英文描述均不断词、不丢行。
- **对战设置页重排**：`BattlePage.setup()` 改为卡片式，顺序为题库（公共/个人 Segmented）→ 科目（Dropdown）→ 主题（Dropdown，随科目联动）→ 题量（3/5/10/∞ Segmented）→ 更多设置（对手等级/初始血量/AI）→ 按钮。新增状态变量/联动方法（题库切换重置科目主题、科目切换刷新主题、题量提示匹配数），筛选值跨重建保留（battle page 切换海克斯选择会重建 setup）。
- **∞ 无限题量**：`_prepare_match()` 在 `count=="∞"` 时设为 `self.infinite=True` 并取全部匹配题；`advance()` 在题数用尽但双方仍有血时重新洗牌、`index=0` 继续，直到一方血量归零才进结算。`__init__` 初始化 `infinite=False`。
- **关键 bug 修复：Configure/对战设置页组件全部失效**（只有 Subject 能点）。根因：`modern.Interactive._face_current()` 无条件调用 `self._face()`，但 `Segmented`/`Stepper`/`Dropdown`/`Toggle` 都没定义 `_face()`，press/release 回调在 `_activate()` 之前抛 `AttributeError`，控件全部静默失效。改为 `getattr(self,"_face",None)` 安全调用（与 `_animate_face` 的 `hasattr` 保护一致）。实战诊断确认修复：难度 0→hard、限时 0→1 均生效。新增回归测试 `test_interactive_controls_without_face_still_activate` 锁住。
- **设置页重置成就**：`AchievementStore.reset()` 用全新默认文档清空解锁与统计（不改类级 DEFAULT，返回清除数量）；Settings 新增「成就」卡片 + 「重置本账号成就」按钮，`_reset_achievements()` 带确认对话框、访客守卫、错误提示。8 条英文文案补齐。
- 测试：新增/重写多个用例（∞ 循环、设置页控件、reset、成就换行相关），全套 **189 项通过**，语法检查通过。文档同步。

## 可换肤立绘皮肤包 + hell 补齐三态 · 2026-11-20

- 用户要求补齐 hell 模式的一般 / 答对 / 答错立绘，并按换肤结构存储以便将来开放换肤功能。
- 新增两张素材抠图（泛洪从边缘去背、羽化 0.6px、裁透明边）：黑底愤怒脸 → `hell/normal.png`；白底左右合图在 x=890 切开 → `hell/correct.png`（绿勾）/ `hell/wrong.png`（红叉）。保护了气泡白底、白发、星星、白色描边等内部白色。
- **皮肤包结构**：`assets/battle/skins/{default,hell}/` 各含 7 张独立透明 PNG（normal/thinking/correct/wrong/attack/attacked/die），`skin_registry.json` 声明清单与文件映射。default 由旧 `expressions.png` 三帧 + `ai_assistant_*.png` 迁移，normal 复用 thinking；hell 由原四张 + 新三张组成。删除旧 `assets/battle/hell/` 目录。
- 新增 `learning_platform/skins.py`：`load_registry()`（缓存）、`skin_for_difficulty()`（地狱→hell）、`portrait_path()`（请求皮肤→default→旧扁平文件逐级回退）、`available_skins()` / `is_sheet()`。
- `battle_ui.py`：`_skin_id` / `_hell_art` 改走皮肤模块，`_portrait_source()` 统一从皮肤包解析（独立 PNG，`sheet=False`）。
- 测试：重写 `test_hell_difficulty_uses_hell_skin_pack`，新增 `test_skin_packs_have_all_states` / `test_skin_store_difficulty_and_fallback`。全套 182 项通过。文档 ASSET_IMAGES / BATTLE 同步。

## 地狱难度替换 hell 立绘 · 2026-11-20

- 用户提供四张 hell 风格立绘（黑红哥特洛丽塔），要求地狱难度对手换成这套。
- 抠图：四张 JPG（三白底 + attack 黑底）用泛洪填充从边缘去背、边缘羽化 0.6px、裁透明边，输出 `assets/battle/hell/hell_{thinking,die,attack,attacked}.png`（RGBA）。泛洪只删连通边缘的纯色，保留角色内部白色（眼睛高光、小天使、能量波）。
- `battle_ui.py` 新增 `_hell_art` / `_portrait_source()`：地狱难度时 thinking/attack/attacked/die 走 hell PNG（单帧 `sheet=False`）；correct/wrong 不在 hell 套内，回退原 `expressions.png` 雪碧图；文件缺失也回退普通立绘，避免空图。`show_expression()` 统一走 `_portrait_source()`。
- 新增 `test_hell_difficulty_uses_alternate_portraits`；全套 180 项通过。

## 血条与卡片中间分界对齐 · 2026-11-20

- 用户发青线标注图：血条行与卡片行的左边缘/右边缘/中间分界应对齐，指出中间错位约 48px、右侧约 18px。
- 根因：血条用对称 padx `(0,SPACE_2)`+`(SPACE_2,0)`，而卡片用不对称的 `(0,SPACE_3)`+`(0,0)`——右卡比左卡宽 12px、中间缝偏移。
- `battle_ui.round()` 改为两卡复用血条的对称列结构：左卡 `(0,SPACE_2)`、右卡 `(SPACE_2,0)`，两列等权。canvas bbox 换算实测血条与卡片同为 x=288→1072、中间缝中心同为 x=680。
- 回归测试新增等宽 + 对称 padx 断言；全套 179 项通过。

## 底部 dock 对称网格重构 · 2026-11-20

- 用户反馈底部左右下角的得分卡文字/数字框与中间对战数据框挤在同一水平带，content 被夹住看不清，且嫌布局是硬编码像素、不像 HTML 自适应。
- `battle_ui.py` 底部 dock 改为两行对称 grid：col0/col2 用 `uniform="score"` 放左右得分卡（等宽镜像），col1 `weight=1`（等价 CSS `flex:1`）自适应；row0 放 clock，row1 放下移的对战数据输出框。数据框不再与得分卡同一水平带。
- clock 层级少一层（clock→panel→dock），同步更新测试断言；新增对称列、数据框下移行的断言。全套 179 项通过。
- 实测：左右卡各 218px 关于中心对称，中间列 572px 自适应，数据框 y 低于 clock，无重叠。

## 对齐问题二次修复（滚动条场景）· 2026-11-20

- 用户反馈上一轮「都设 SPACE_4」后右侧仍内缩约 30px。根因：① 垂直滚动条只压缩 `canvas` 不压缩 `outer`，按 canvas 宽算的 body 少一截；② body frame 的横向 padding 与 canvas window 的 inset 叠加。
- `Application` 新增 `_body_match_outer`，`set_body_side_pad(px, match_outer=True)`；`_on_canvas_configure` 在 battle 页改用 `outer.winfo_width()` 计算 `content_w`，`clear()` 复位。battle `round()` 把 body padding 改为 `(0, SPACE_1)`，只保留 canvas window 一层 inset。
- 回归测试改用 canvas bbox 比较（root 坐标对 canvas 内嵌控件有 −16px 偏差，不可靠）；实测有/无滚动条两种状态下血条与题目卡左右边缘完全重合。全套 179 项通过。

## 题目卡对齐血条 + 中间文字真正居中 · 2026-11-20

- 修复题目卡比血条窄约 64px 的错位：`Application._body_side_pad` / `set_body_side_pad()` 让 battle 页的 canvas window 与 body frame 横向内边距同时用 `SPACE_4`（与固定 header/dock 一致），`clear()` 复位 `PAGE_PAD`。两张题目卡现与血条共享完全相同的左右外边缘。
- 修复中间「正确答案 + 解析」未居中：tk.Text 内建 `all` tag 在本平台不响应 `justify`；改用具名 tag `aligned` 并覆盖到 `end`（含尾换行），短行实测已居中。
- 新增回归测试，全套 179 项通过。

## 得分卡布局精修 · 2026-11-20

- `ScoreCard` 四个分段框改为常驻（未结算用「·」占位）；正确/速度/加成/总分的描述上移到各自框正上方，整行在 Canvas 内水平居中，去掉与血条重复的「{名字} · 得分」标题。
- 中间对战数据列的全部文字居中：`AssistantReply` 支持 `justify`，tk.Text 通过内置 `"all"` tag 设置对齐（无 widget 级 `-justify` 选项）。
- 全套 178 项测试通过。

## 对战页固定状态栏 + 题面免滚动 · 2026-11-20

- 新增 `Application._battle_header()`，把海克斯横幅 + 双方血条钉在 Quiz battle 白线下方（挂 `outer`，不随题面滚动）；`clear()` 切页时一并销毁。血条高度 44→34、`BAR_H` 14→12。
- 题数/计时器 `self.clock` 从随滚动的 body 顶部移到底部控制台中间列（`Question.TLabel`），两侧分段得分卡压到 44px、中间对战数据 2–4 行，三栏都保留但明显变矮。
- 压缩题干区：卡片内边距、AI 思考区高度 7→5、立绘 190→160、题图宽度 280→160、选项 pady 2px、body padding 收到 `SPACE_1`。1100×760 下 body 请求高度与视口齐平，右侧无滚动条，题目与全部选项一屏可见。
- 新增回归测试 `test_battle_header_fixed_and_clock_in_dock` 验证固定头部层级、clock 归属与高度压缩。全套 178 项通过。

## 对战底部三栏结算面板 + 血条并排 · 2026-11-20

- 按用户参考图把顶部双方血条从「上下两行」改回「左右并排同一行」：两列等宽 grid（`row=0`，`column=0/1`），各自仍是名字 + ♥ + 血条 + 数值，几何完全对齐。
- 底部结算从一整块纯文本改为三栏面板：左右是 `battle_result.ScoreCard` 分段得分卡（正确 + 速度 + 加成 = 总分，四段各自带框、总分用强调色），中间是「对战数据」对话框只放正确答案 + 解析 + 海克斯提示，去掉冗余得分算式。保留 `self.result` 组件与测试接口。
- 新增英文文案（`{0} · 得分`、`等待结算`、`速度`、`加成`、`对战数据`）。回归测试补充血条并排几何断言、分段得分卡数值/帧结构、对话框不再含得分算式。全套 177 项通过。

## 成就徽章边框对齐海克斯卡牌 · 2026-11-20

- 成就卡边框改为与海克斯卡牌完全相同的机制：用 `augment_ui._rounded_points()` 采样圆角周长，逐段 `create_line()` 绘制（24 段），不再用单个 `round_rect(outline=...)` 平描边。
- 棱彩 / 魔王解锁后跑 `edge_colors()` 逐段流光（魔王红白高光、棱彩彩虹），与卡牌 `_shimmer()` 一致；锁定的魔王保留暗色流光，白银 / 黄金及锁定棱彩为静态分段等级色边框。
- 回归测试 `test_locked_badge_shows_tier_border_and_label` 增加断言：锁定卡与棱彩解锁卡都具备多段 line 边框，棱彩各段颜色不统一。

## 成就达成条件常显 · 2026-11-20

- 未解锁的成就卡不再隐藏达成条件：现在解锁 / 未解锁都显示成就名称、等级标签和达成条件（`description`），未解锁仅以暗色等级色调 + 右上角「未解锁」标记区分，解锁则显示完整配色和 ✓。边框等级色、魔王档流光等既有视觉保持不变。
- 回归测试 `test_locked_badge_shows_tier_border_and_label` 增加断言：锁定卡也必须渲染达成条件文案。

## 魔王契约飘字崩溃修复 · 2026-11-20

- 修复"选魔王海克斯后一堆 bug"的根因：动效开启时，`_stage_damage()` 调用 `ai_bar.float_text("×3")`，而 `battle_fx.py` 引用的是原始 `tokens` 门面（颜色只存在于 `palette()`），飘字帧里却写了 `T.BG`，同步抛出 `AttributeError: module 'learning_platform.tokens' has no attribute 'BG'`，直接中断 `finish_round()`（结果文本不显示、自动进题失效）。改为 `T.palette()["BG"]`，与同文件其余取色方式一致。
- 修复次生问题：血条数值补间的每一帧都会 `delete("all")` 重绘，把刚创建的 ×3 飘字一起抹掉，导致"三倍伤害特效没生效"。现在只删除带 `bar` tag 的血条本体，飘字带 `float` tag 得以完整播放。
- 新增回归测试 `test_demon_damage_float_with_motion_enabled`：强制动效开启走 `tween.frame(0)` 路径（旧测试在动效关闭下走 `after` 分支，漏掉了该 bug），验证 `finish_round()` 不再抛异常、飘字实际绘出。回退到旧代码时该测试能精确复现同样的 `AttributeError`。
- 曾临时恢复 MAT012 以消除当时的 core 测试失败；后确认该题由用户有意删除，已在后续条目撤回。
- 全套回归 177 项通过。

## Tk 测试偶发 TclError 根治 · 2026-11-20

- 说明此前所谓"偶发错误"的真实形态：全套测试连续创建 / 销毁约 170 个 Tk root 后，Windows Tcl/Tk 出现 `_tkinter.TclError: invalid command name "tcl_findLibrary"`、`tk.tcl` 无法 source、`image create photo` 失败；每次落在不同测试，重跑即过。
- 测试层改为进程内单一隐藏 Tk root（`tests/__init__.py` 的 `fresh_tk_root()`）：每例前取消残留 `after`、解绑根与全部子控件的 Python 回调、销毁旧控件，再复用同一个解释器；6 个 GUI 测试模块统一接入，不再反复初始化 Tcl。
- 应用层加固：登录页装饰图改走有界 `image_cache.source_image()`，并对 `TclError / OSError / ValueError` 静默降级；同一 root 上的第二个 `Application` 复用根级勾选图与 `Checkmark.indicator` 元素，避免 "Duplicate element" 错误。
- 连续多次运行 `py -3 -m unittest discover -s tests` 全绿且无残留 `Exception in Tkinter callback`，测试耗时也明显下降。

## 魔王回合计分修正与血条对齐验证 · 2026-11-20

- 修复魔王契约下大肥鱼答对却计 0 分、文字标红的问题：7 秒限时只约束玩家，对手仍按原 30 秒响应截止与计分窗口判定，不再被玩家限时误伤。
- 双方血条继续共用按字体实测的统一名字列宽，新增轨道细描边，并把血条起点、终点和数值 x 坐标写入控件属性，回归测试直接验证两行几何完全一致。
- `docs/BATTLE.md` 同步说明玩家 / 对手两套时间边界；新增魔王慢速正确作答的 GUI 回归用例。

## Demon border polish and badge presentation · 2026-11-20

- Reworked the Demon border into a deep-red edge with a travelling white/red highlight, replacing the harsh per-segment black/white/red strobe.
- Achievement badges are now ordered by tier (Demon > Prismatic > Gold > Silver); locked badges show a tier-tinted border and the tier label, unlocked badges show full text, colours and check mark.
- Demonic Pact now shows an explicit triple-damage note and floating "x3" numbers over the opponent's health bar.

## 魔王边框打磨与成就展示 · 2026-11-20

- 魔王边框改为深红底 + 白/红高光流动，取代原先生硬的黑白红跳色。
- 成就按稀有度降序排列；未解锁显示等级色边框与等级标签，解锁后显示完整文字与背景色。
- 魔王契约三倍伤害补上结算提示与对手血条上的「×3」飘字。


## Demon-tier augment · 2026-11-20

- Added a fourth rarity above Prismatic -- Demon. The augment draft is now one card per tier (Silver / Gold / Prismatic / Demon).
- Added the "Demonic Pact" augment: 7-second rounds in exchange for triple damage dealt (damage taken is unchanged).
- Demon tier and the Demon Slayer badge now use a black / white / red strobe border on cards, banners, badge wall and unlock toasts.

## 魔王档海克斯 · 2026-11-20

- 新增凌驾棱彩之上的第四档稀有度「魔王」，发牌改为四档各一张；新增魔王契约卡（7 秒限时、造成伤害三倍，自身受伤不变）。
- 魔王档与「大魔王猎手」徽章统一使用黑白红交替闪烁边框，覆盖卡牌、每轮横幅、徽章墙与解锁弹窗。


## Hextech augments, damage staging and achievements · 2026-11-20

- AI battle now opens with a three-card Hextech augment draft (Silver / Gold / Prismatic), one card per tier; selected effects last the whole match and are applied through a single runtime.
- Replaced numeric HP text with animated Canvas health bars, added Big Whale damage poses (attacked / die / attack) from transparent PNGs, and auto-advance to the next question after a short hold with a "loading next question" hint.
- Added an achievement system with 8 badges, per-account JSON persistence, instant unlock toasts and a dedicated sidebar badge wall.

## 海克斯强化、掉血演出与成就系统 · 2026-11-20

- 答题对战新增开局三选一海克斯强化（白银 / 黄金 / 棱彩），每档一张、整局生效，统一由效果运行时承接。
- 血量改为带补间的 Canvas 血条（两条对齐同一列、不遮挡名字），新增大肥鱼被砸 / 倒地 / 喷水三种动作立绘（透明 PNG），结算停留 3 秒后自动进下一题并显示提示。
- 新增成就系统：8 枚徽章、按账号 JSON 持久化、解锁瞬间弹窗提示；入口在对战设置页并可原路返回，徽章绑定账号，游客显示注册引导。


## Documentation consolidation · 2026-11-19

- Moved the root README, design guide, specification, contribution guide and original prompt into docs; moved the image directory guide to ASSET_IMAGES.md.
- Added a documentation index, AGENTS.md, a code of conduct and an all-rights-reserved LICENSE; updated relative links in current documentation.
- Kept archives, the runtime dependency list and sample exports in their existing locations.
- Provided the newly added guidance in English first, followed by Chinese.

## 文档集中整理 · 2026-11-19

- 将根目录的 README、设计说明、需求规格、贡献指南和原始提示词集中到 docs；图片目录说明迁入 ASSET_IMAGES.md。
- 新增文档索引、AGENTS.md、行为准则及保留所有权利的 LICENSE，更新当前文档相对链接。
- 保留归档目录、运行依赖清单及示例导出文件的位置。
- 新增说明采用英语优先、中英双语。

## Portable one-file build · 2026-11-16

- Added `WhaleMate.spec` and `build_exe.bat`: a windowed single-file Windows exe (~38 MB) bundling Python 3.13, Tcl/Tk, ReportLab, question banks and artwork.
- Frozen builds use a writable `WhaleMate_data/` root beside the exe (falling back to `%LOCALAPPDATA%\WhaleMate`), seeded with read-only resources on first launch, so accounts and progress survive restarts.
- Only distributable resources are bundled; local users.json, profiles and progress are excluded.
- Added `--check` and `--smoke` self-tests, frozen-aware pip skipping, and console-free error reporting.
- Verified in a clean temporary directory: Tk 8.6 window, real PDF generation, full Application construction, 3 question banks and 69 images.
- Renamed the Windows launcher `start.bat` to `start_windows.bat`; current docs use the new name (archived snapshots keep the original).

## Windows 单文件免安装版 · 2026-11-16

- 新增 `WhaleMate.spec` 与 `build_exe.bat`：产出约 38 MB 的无控制台单文件 exe，内含 Python 3.13、Tcl/Tk、ReportLab、题库与图片。
- 打包版在 exe 旁使用可写的 `WhaleMate_data/` 作为项目根目录（只读位置回退 `%LOCALAPPDATA%\WhaleMate`），首次启动同步只读资源，账号与进度不会因重启丢失。
- 只打包可分发的只读资源，本地 users.json、profiles 与进度文件不进入交付包。
- 新增 `--check` / `--smoke` 自检（结果写入 `runtime_check.txt`），打包版跳过 pip 自检，无控制台时以弹窗与日志记录启动错误。
- 在独立临时目录验收通过：Tk 8.6 可建窗、PDF 可生成、完整界面可构造、3 份题库与 69 张图片齐全。
- Windows 启动脚本由 `start.bat` 更名为 `start_windows.bat`，当前文档引用已同步（归档快照保留历史名称）。

## Launcher dependency bootstrap · 2026-11-15

- `launcher.py` checks requirements.txt on startup and installs missing optional packages with the running interpreter's pip; failures, offline machines and timeouts never block the standard-library core.
- Missing Tcl/Tk and headless-display errors now print platform-specific repair steps instead of the generic "install Python" hint; `start_windows.bat` and `start_mac.command` carry the same guidance.
- Added 13 launcher unit tests covering requirement parsing, install, failure, timeout and per-platform messages without network or display access.

## 启动器依赖自检 · 2026-11-15

- 启动时检查 `requirements.txt`，缺失的可选依赖由当前解释器的 pip 自动安装；失败、离线或超时不阻断核心练习。
- 缺少 Tcl/Tk 或无图形桌面时改为按平台输出修复指引，`start_windows.bat` 与 `start_mac.command` 的兜底文案同步更新。
- 新增 13 项启动器单元测试，覆盖依赖解析、安装、失败、超时及各平台提示，不访问网络、不打开窗口。

## English-first documentation and Unicode punctuation · 2026-11-13

- README, the authoritative specification and the SRS mapping guide now have matched English-first and Chinese sections, with current permissions, companion/battle behaviour, exports and limitations consolidated.
- Original documents remain unchanged in `docs/archive/*PRE_BILINGUAL_20261113.md` for historical reference; contradictory legacy claims no longer appear as current requirements.
- PDF paragraphs switch fonts for Unicode runs, including full-width punctuation such as `！`, while retaining Helvetica for Latin text and preserving user wording.

## 英文优先双语文档与标点修复 · 2026-11-13

- README、主规格和 SRS 对应说明整理为英文在前、中文在后，内容覆盖当前权限、伴学/对战、导出及限制。
- 三份原文完整保存在 `docs/archive/*PRE_BILINGUAL_20261113.md`，过时说明不再作为当前需求。
- PDF 对 Unicode 文本段使用字体回退，覆盖全角 `！`，英文仍使用 Helvetica，不替换用户笔记内容。

## 英文导出与时间格式 · 2026-11-13

- 错题和学习成绩 PDF 的全部固定文案、页脚及文档属性统一英文，不随界面语言改变；保留题目和用户笔记原文。
- 英文使用 Helvetica 字体，中文用户内容保留字体回退；错题配图与笔记继续导出。
- PDF/CSV 记录时间统一本机时区的 yyyy/mm/dd hh:mm:ss，PDF 显示导出时区，错题最近作答不再直接输出 ISO 时间戳。
- 英文导入预览补齐 Validation passed 及重复题目提示，增加实际表格、导出文案及时间格式回归检查。

## 提交前审查修复 · 2026-11-13

- 普通个人题库与管理员监管统一使用权限访问服务；账号在编辑期间被停用后，保存和删除都被拒绝。
- 对战先检查截止时间，再接收决策；30 秒后返回的有效结果同样按作废处理，不扣血、不累计分数。
- 关闭窗口时取消残留 Tcl 定时器，避免登录装饰、轮询和对战回调在控件销毁后执行。
- GUI 用例改为登录账号测试错题本，单独验证游客限制；提示词断言同步两阶段伴学功能。
- Ruff 对公开兼容导出明确声明 F401 例外，备份文件不参与应用代码检查，截图工具的 DPI 初始化保留必要导入顺序。
- 使用真实本地接口验证 MAT009 图片题：返回答案 5，包含三段摘要；未记录密钥。

## 界面重复工作清理 · 2026-11-13

- 对普通练习与对战共用有上限的图片缓存，复用源图及裁剪表情，文件修改时自动失效；源图最多 16 张，表情最多 12 张。
- 对战倒计时与练习倒计时仅在显示文字变化时重绘；结果区域移除布局回调内的 update_idletasks，避免嵌套布局刷新。
- 未启用点赞筛选时只更新被点击爱心，不再重建全部学习记录；启用筛选时仍刷新以保持查询结果正确。
- 卡片相同尺寸不重复绘制，Canvas 宽度不变时不重复提交布局；旧练习计时回调不再触碰已销毁控件。
- 连续五轮切页抽查未观察到图片对象或定时器逐轮增加；整轮耗时有波动，不据此承诺整体提速比例。补充缓存容量、对象复用与点赞局部更新检查。

## 对战异常结算与点赞颜色 · 2026-11-13

- 对手接口失败或无有效决策的超时不再按错误答案扣血；该轮作废、不累计成绩，显示错误原因并允许原题重试。
- 对战使用独立 JSON 系统约束、JSON 输出模式及 800 token 输出额度，避免伴学提示词和三阶段摘要格式冲突；普通伴学仍为 320 token。截断回复明确报错。
- 学习记录的已点赞爱心为主题蓝，未点赞为空心白色，点击后保持对应颜色。
- 接口异常不扣血、JSON 请求参数等回归检查通过。

## 对战视觉输入 · 2026-11-13

- 对战 API 支持发送题干和选项图片，标明所属选项，官方接口图片题使用视觉模型 deepseek-flash。
- 增加图片路径、格式及大小检查，仍不发送答案和解析；文字伴学入口保持原行为。
- 对战玩家侧显示选项图片，补充图片请求编码、选项标记及异常输入测试。

## 对战三阶段展示 · 2026-11-13

- 作答区按读题、比较选项、选择检查三段替换文字，前段消失，不再堆积提交状态。
- 阶段进度按对手等级的模拟时间分配，答案仍在双方作答结束后揭晓。
- API 可返回三段简短教育摘要，随决策保存并在结算展示，不额外请求接口。

## 对战决策记录 · 2026-11-13

- API 作答返回绑定本题的选项及简短依据，保留到结算后公开；不再另行生成事后解释。
- 移除模拟思考阶段轮播；明确 API 决策与本地概率模拟的区别，配置密钥时默认 API。
- 校验决策题目、选项、耗时和依据；补充结构校验及错误选项保留测试。

## 个人题库监管与人员管理布局 · 2026-11-13

- 管理员可在题库中心按账户管理所有个人题目，人员管理也提供选中用户的题库入口。
- 访问服务重新校验操作者权限、目标 UUID 和账户存在性，修改前自动备份，保留学生隔离及原用户表结构。
- 人员管理新增四项统计卡，表格交替行色、双击编辑、底部固定圆角操作栏，缩短按钮文案。
- 补充管理员修改/删除、跨账户隔离、游客与学生越权、管理员撤权的回归测试。

## 答题反馈精简 · 2026-11-13

- 英文错选标记由 Your pick 缩短为 picked，避免右侧文字拥挤。
- 答错反馈移除重复的 Try again，保留错题本提示、正确答案及完整解析；反馈继续使用本地题库数据，不调用接口。
- 补充错选标记及本地答错反馈回归测试。

## 题库导入整改 · 2026-11-13

- 题库页采用圆角主要操作、底部固定工具栏、交替表格行和 Enter 搜索。
- 导入预览显示完整错误原因及双向滚动，失败换文件清空旧预览和统计，确认按钮随有效题状态启用。
- 预览绑定目标题库；服务层校验会话，确认时再次按 ID/内容去重，CSV 校验表头与列数。
- 提供不同内容的 JSON/CSV 测试文件，各 3 题，补充跨账户预览、权限撤回、重复提交及预览后变化测试。
- 管理员维护他人题库只评估，未开放，详见 QUESTION_BANK_IMPORT.md。

## 学习日志改版 · 2026-11-13

- 新增记录收藏、学习笔记、日期范围及收藏/笔记组合查询。
- 使用统计卡和简洁记录卡，时间按本机时区统一格式显示，取消重复时间及分数输出。
- 学习记录页去除 CSV，PDF 仅输出查询快照并包含收藏与笔记。
- 元数据按账户目录隔离，新建 history_notes/history_ui 模块，保持旧成绩兼容。
- 补充账户隔离、笔记持久化、日期边界、组合查询及页面回归用例。

## 答题对战 · 2026-11-12

- 增加所有角色可见的对战入口、四档模拟对手、同题倒计时和分项计分。
- 独立 battle/battle_ui 模块沿用主题令牌、圆角卡片与自绘选项按钮。
- Local/API 双提供者接口，API 复用现有客户端配置，后台请求并验证返回结果。
- 增加计分边界、超时与对手概率配置测试，完整回归 94 项通过。

## v2.7 题目插图放大：3 倍分辨素材 + 按列宽自适应 · 2026-11-11

- 根因：`show_image()` 的缩放上限是 480×220 设备像素，而所有题目素材都是 480×270——高度上限一项就迫使 `subsample(2)`，插图实际只有 240×135，在高 DPI 下相对文字显得很小。
- 素材：`scripts/generate_question_art.py` 保留 480×270 设计坐标，新增 `ScaledDraw` 代理把绘制调用映射到 `SCALE=3`（1440×810），再按 `SUPERSAMPLE=2` 渲染后 LANCZOS 降采样，线宽与文案都是最终分辨率直出，不再是放大糊图；画布改 RGBA，四周留白透明，插图卡片可直接浮在任意底色上。
- 尺寸：`show_image()` → `_fit_image()` 按宿主列宽挑「放得下的最清晰整数降采样」（列宽 −16px、高度上限 420 设计 px），并把结果按 factor 缓存在 label 上；宿主 `<Configure>` 时重算，顺便修正新建答题列宽为 1 的首帧。答题页 150% 下 720×405（约占列宽 70%，是原来的 2 倍），100% 下 720×405，窄窗口自动退到 480/360。
- 融合：`PhotoImage` 的 alpha 会与控件背景合成，因此图片容器改用 `tk.Frame/tk.Label` 并从宿主取底色（`_blend_color()`，先经典 `bg` 再 ttk 样式查表），避免深色主题下出现亮色方块。
- 错题本与题目编辑器预览通过 `max_width=360` 保持紧凑；编辑器 `render_image()` 改为复用同一条管线，删除重复的固定缩放逻辑。
- 内存：只有屏上显示的那一份图进 `Application.images`，1440×810 原图随 label 生命周期释放。
- 新增回归 `test_question_art_fills_the_question_column`（factor 计算 + 实测插图 ≥55% 且 ≤100% 列宽）；共 **92 项全通过**。验收截图 `.workbuddy-ai/preview/v4-*.png`（`.workbuddy-ai/capture_quiz_art.py` 可复现）。

## v2.6 首页 Ask AI 卡片重做：主色系语义色 + 自适应 Q 版立绘 · 2026-11-11

- 新增语义色令牌 `AI_INPUT_BG` / `AI_INPUT_EDGE` / `AI_REPLY_BG` / `AI_REPLY_EDGE`，替换原来借用的中性灰 `HOVER`。浅色下回复区是主色浅底的 72% 叠加，深色下 `PRIMARY_SOFT` 与表面过近，改用 `mix(surface, primary, 0.10)` 保证面板可见。
- 新增 `modern.SoftPanel`：无阴影的圆角着色面板，可选 1px 描边并支持聚焦时把描边换成主色（输入区焦点态）。
- 首页「问问 AI」重做（`_build_home_ai()`）：标题（主色圆点 + Ask AI）→ 输入面板（两行文本域 + 面板内发送按钮 + Enter 提示行）→ 回复面板占满剩余高度。输入框 Enter 发送、Shift+Enter 换行，发送成功后清空、失焦恢复占位符。
- Q 版形象改为回复区空闲态立绘：按面板实际 `<Configure>` 尺寸自适应放大（上限 320 设计 px），用整数 `PhotoImage.subsample` 缩放，不引入 Pillow 依赖；形象与问候语作为整体居中，面板过矮（立绘 < 120px）时自动隐藏问候语，避免文字被裁。
- `AssistantReply` 增加 `on_text` 钩子：首次出现状态/回复时隐藏立绘、显示「AI 提示 + 正文」，清空文本时恢复立绘。
- 答题页 `_quiz_ai_panel()` 同步换成 `AI_REPLY_BG` / `AI_REPLY_EDGE`，与首页保持同一套视觉语言。
- 新增回归 `test_home_ai_card_uses_primary_tints_and_idle_portrait`（主色令牌≠HOVER、两套主题、空闲/回复两态切换、立绘已加载）；共 **91 项全通过**。
- 文档：`DESIGN.md` v2.6（新增 v2_6_home_ai 章节）、`README.md` 同步。验收截图 `.workbuddy-ai/preview/final2-home-*.png`（`.workbuddy-ai/capture_ai_card.py` 可复现）。

## v2.5 答题页 Ask AI 上下结构、英文纯净度与列表页撑满 · 2026-11-11

- 答题页 `show_question()` 改为 50/50 两列 + 加权行，两侧都随视口高度拉伸；新增 `_quiz_ai_panel()` 把原来「回复在左、头像和按钮在右」的短卡片改成上下结构：标题与「每题可询问一次」说明 → 全宽可伸缩回复气泡 → 圆形头像 + 宽幅自绘按钮（按钮文案同时承担「Asked for this question」状态）。每题一次询问的锁定逻辑不变。
- `ai_assistant.py` 新增 `SYSTEM_PROMPTS = {zh, en}` 与 `system_prompt()`；英文控制词强制 **ALWAYS answer in English**。`AiAssistant.ask(message, language)`、`question_message(question, language)` 接收界面语言，`gui.py:_request_ai()` / `ask_current_question_ai()` 统一传 `self.tr.language`；校验与网络错误也双语化。英文界面下 AI 回复固定英文，即使题干/选项含中文。
- 难度可见标签改为 i18n 键（`_difficulty_label()`），英文模式显示 `All / Easy / Medium / Hard`；配置页右上角摘要不再出现「全部」。语言选项「简体中文」在英文模式显示 `Simplified Chinese`。`en.json` 补 13 条词条。
- 修复列表页空白：题库管理与用户管理 `Treeview` 所在 grid 行补 `rowconfigure(0, weight=1)`，基础行数 10/12 → 18，末列 `stretch=True`；所有列宽改经 `T.px()`，修掉 150% DPI 下 `Diffic…` / `Mathemati…` / `Vocabular…` 截断。导入预览表同步缩放。
- 配置练习页 `SoftCard` 改为 `fill="both", expand=True`，用弹性 spacer 把 footer 固定在卡片底部，消除卡片下方大块空白；错题本/学习历史的空状态卡片同样撑满视口。
- 新增回归：AI 英文提示词/英文提问/英文报错、英文界面中文残留扫描（含 Canvas 自绘文字）、Ask AI 加权行、两张表格拉伸、AI 请求语言链路；共 **90 项全通过**。
- 文档：`DESIGN.md` v2.5、`README.md`、`docs/AI_ASSISTANT_PROMPT.md` 同步。验收截图 `.workbuddy-ai/preview/v25-*.png`（`.workbuddy-ai/capture_v25.py` 可复现）。
- 说明：题库题干与选项属于数据而非界面文案，ENG001 等英语词汇题的选项本身是中文，按 SRS「题库内容保留原文」不翻译。

## v2.4 布局与高 DPI 显示修复 · 2026-11-11

- 两个启动入口（`launcher.py`、`gui.main()`）新增 `maximize_startup()`，Windows 用 `root.state("zoomed")` 默认最大化；`start_windows.bat`、`main.py`、`python -m learning_platform` 全部继承。
- 滚动画布的 body 窗口改为按视口高度拉伸，首页四卡在最大化窗口下铺满页面，消除下方大片空白；首页卡片内距统一为 `T.SPACE_5`(24)，内部间距全部经 `T.px()` 缩放。
- 修复 `_strip_focus()` 回归：clam 主题把 `Radiobutton.label` / `Checkbutton.label` 嵌在 `.focus` 节点内，旧实现删整节点导致设置页单选项只剩圆点；现在提升子节点再删焦点框。
- 移除全项目写死的 `wraplength` 常量，改为 `<Configure>` 事件按控件真实宽度自适应（`label()`、设置页 `fit()`、配置页列 helper），修复高 DPI 下说明文字挤成窄列、登录页工具栏被裁成 `gh n`、首页空状态文案被截尾。
- 登录页表单加宽（`CARD_WIDTH` 420 → 520 设计 px）、标题升级 `TYPE_HERO`、表单列居中留白，改用圆角柔和阴影卡片；学科标题与表单间距按 8pt 栅格放大。
- 设置页分区内距统一 24、说明文字铺满卡片宽度，外观/语言/动画分组改为整行呼吸感布局。
- 默认初始语言锁定为英文：`Translator` 新建配置 `{"language": "en"}`，`data/settings.json` 亦为 `en`，新增 `LanguageTests.test_new_profile_starts_in_english` 回归测试。
- `DESIGN.md` 升级 v2.4 并补充布局/焦点/换行规则；`README.md` 同步启动、主题与测试数量说明。
- 验证：`py -3 -m py_compile learning_platform/*.py launcher.py` 通过，`py -3 -m unittest discover -s tests` **85 项全通过**；`.workbuddy-ai/preview/full-dark-*-{125,150}.png` 与 `redesign-*.png` 截图重新采集，100/125/150% 均无裁切。

## 问问 AI · 2026-11-05

- 设置页新增 DeepSeek 兼容接口、模型和加密 API Key 配置。
- 首页新增单轮学习聊天卡片；网络请求使用后台线程，避免阻塞界面。
- 答题页新增“问问 AI”，仅发送题干与文字选项，每题成功回复后锁定。
- 限制单次输入 2500 字符、输出 320 tokens，并使用低温度控制回答长度与稳定性。
- 增加独立控制词、隐私说明和 API 请求、敏感字段排除、Key 非明文存储测试。

## 公共题库导入与统一返回导航 · 2026-10-31

- 管理员可在公共题库中心批量导入 JSON/CSV，沿用校验、预览、重复保护、确认和备份流程。
- 主要页面顶栏统一增加左侧返回箭头，标题后移；编辑、导入等子页面返回对应上级列表。
- 用户管理按钮改为同一行工具栏，移除底部难以发现的返回按钮。
- 增加公共题库模板导入和顶栏返回按钮回归测试。

## 统一题库中心与布局整理 · 2026-10-31

- 将题库管理、个人题库导入合并为侧边栏“题库管理”；用户管理也迁入侧边栏。
- 管理员可维护公共及个人题库，普通用户可完整增删改查自己的题库，访客不显示管理入口。
- 题库中心整合列表、筛选、图片、新增、编辑、删除和 JSON/CSV 批量导入。
- 错题 CSV 补齐题目结构并可重新导入；官方 JSON/CSV 模板加入实际导入回归测试。
- 移除首页底部管理按钮及设置、结果、错题、历史、用户管理中的重复正文标题；答题进度与底部操作继续固定，仅题目内容滚动。
- 新增个人题库 CRUD、公共 ID 保护、错题导入、模板可用性和分角色侧边栏测试。

## 每日目标业务调整 · 2026-10-31

- 将“今日目标”和“设置每日目标”合并为一张首页卡片，右上角扳手打开设置窗口。
- 每日计划新增题库、科目和难度条件；首页以小号文字显示当前条件。
- “继续今日练习”直接按计划和当天剩余题数随机抽题，不再重复进入练习配置页。
- 兼容旧版学习计划文件，并新增设置持久化和直接开始每日练习的回归测试。
- 公共题库与个人题库继续物理隔离；个人计划只读取当前账户的题库文件。

## 登录记忆 · 2026-10-29

- 成功登录后自动显示上次账号。
- 登录页增加“记住密码”；Windows 使用 DPAPI，macOS 使用系统钥匙串。
- 取消勾选并成功登录后不再自动填写密码；`data/login_state.json` 不进入版本控制。
- 新增加密存储、损坏状态恢复及完整登录流程测试。

## 1.3 · 2026-10-27

- 统一字体、配色、按钮状态和管理表格，首页加入统计摘要与自适应功能卡片，答题页加入进度条。
- 顶栏访客文字旁提供登录入口；登录后显示用户名及退出登录/切换账户。
- 登录表单突出主操作，输入框支持 Enter；标题随窗口宽度换行。
- 新增 12 个隔离业务流程用例及顶栏账户导航回归测试，提供分组运行和截图说明。
- 同步 SRS、界面规范和测试文档。

## 1.2 · 2026-10-26

- 选项展示统一为 A:、B:、C:、D:，覆盖练习、错题、编辑器和预览；原答案数据不变。
- 将现有 wutaicheng 一次性升级为管理员，保留密码和 UUID，备份原账户文件；不存在按用户名自动授予权限的逻辑。
- 新增管理员/普通用户及启用状态，普通用户不显示管理入口；管理操作重新校验角色，停用后阻止登录和后续会话操作。
- 新增用户管理：新增、改名、密码重置、停用/恢复、管理员提升/撤销、学习数据查看；保护最后一个启用管理员。
- 新建/重置密码调整为 6–16 位；保留旧密码登录兼容性。
- 新增设置页、中英文界面及语言持久化；题库数据保持原文。
- 新增 17 项权限、用户表单、语言和选项回归测试，并同步 SRS 与维护文档。

## 1.1 · 2026-10-26

- 新增本地注册/登录页面、退出登录、访客入口；密码以随机盐及 PBKDF2-HMAC-SHA256（600,000 轮）摘要保存。
- 注册账户使用 UUID 分隔学习记录；原 `data/progress.json` 保留为访客记录，不自动迁移。
- 新增题库列表、搜索/学科筛选、表单增删改、动态选项、正确答案选择和可滚动预览。
- 新增题干及选项图片上传、预览、替换和解除关联；图片复制至唯一的项目相对路径。
- 编辑/删除前自动备份源 JSON；新题写入 `custom.json`；保留无关记录、未知字段并拒绝过期编辑。
- 原 15 道题和 ID 保留，增加 45 道题，三科各 20 道。
- 更新 SRS FR-10–13、README、模块注释、开发规范及测试；引入 Ruff 开发检查配置，运行仍无需第三方库。

## 1.0 · 2026-10-26

- 从旧命令行项目整理出 Tkinter 离线平台，完成练习配置、判题、图片、错题本、历史和 JSON 原子持久化。
- 提供三科 15 道题和初始 24 项自动化测试。

### 1.3 笔记本适配补充

- 默认紧凑布局，减小按钮、输入框、卡片和表格行间距。
- 设置增加窗口尺寸预设与紧凑开关，立即应用并持久化，启动时按当前屏幕限制窗口大小。
- 增加尺寸边界、偏好持久化、损坏文件保护及界面应用测试。

### 2026-10-28 首页排列调整

- 访客及普通用户的四个功能入口改为两行两列，避免出现三加一排列；管理员六入口保留紧凑三列。


## 2026-10-29 V2 整合更新

当前正式目录为 `D:\develop\workplace\INT6181GroupAssessmentV2`。完整变更、账户迁移、窗口设置及测试范围见 [V2_INTEGRATION](V2_INTEGRATION.md)。本文件先前版本内容保留为历史；当前界面采用 V2 深色主题，测试保留 V2 原有套件。


2026-10-29：新增整轮限时、CSV/PDF 导出、明确的中途退出提示和 Windows 一键启动。使用方式、超时计分规则及修改文件见 [功能说明](FEATURES_3567.md)。PDF 导出新增 reportlab 依赖，核心运行仍使用标准库。


2026-10-29：题数输入改为白底黑字；勾选框使用对勾。PDF 改为蓝白报告样式，包含统计摘要、页脚页码；错题按题分页并加入题干及选项图片、答案与解析，历史使用学科配图。Windows 优先嵌入宋体，保证中文显示。


### 2026-10-29 组员版本规范整理

保留 7807589 的设计，清理导入及未使用变量，将赋值式 lambda 改为具名回调，统一格式。检查与需求差异见 [代码检查记录](CODE_REVIEW_20261029.md)。


2026-10-29 练习交互修复：题数变化同步更新开始按钮；配置页压缩为下拉学科与紧凑筛选，开始按钮固定底部；设置增加滚轮修改选项开关（默认关闭，随窗口设置保存）；答题选项只保留一个字母标记，去掉重复前缀及圆点；提交后原位切换可用的继续按钮，底部操作栏保持固定，长题目及反馈在上方内容区滚动。新增题数同步、滚轮持久化和滚动时按钮可见性回归测试。


2026-10-29 练习布局调整：恢复紧凑学科卡片选择，固定操作栏的主要操作在左侧，返回或结束在右侧；答题进度仅保留圆点连线，移除重复矩形进度条。


答题页进度条固定在顶部标题栏下方；题号只在标题栏显示一次。中间仅滚动题目、选项和解析，底部操作栏固定。离开答题页时移除固定进度区域。


## 2026-11-10 双主题、简约登录页与默认英文

- `ui_tokens.py` 改为运行时可切换调色板（Lights Out 深色 / Daylight 浅色），新增 `THEMES`、`theme_name()`、`set_theme()` 及 NAV_BG、SCROLL_*、CHECK_*、RAISED 等令牌；颜色统一在渲染时通过 `T.<TOKEN>` 读取，去掉冻结调色板的直接导入与函数默认参数。
- `Translator` 新建配置默认英文（`en`），新增 `set_theme()` 将主题写入 `data/settings.json`；已有配置保持原语言，损坏文件仍安全回退且不覆盖。
- `Application.apply_theme()` 重绘 ttk 样式、重建侧边栏与当前页面；登录页工具栏、侧边栏底部和设置 → 外观三处均可切换，练习进行中切换保留引擎与已提交答案。补齐 `configure()` 的 `_nav_key`，保证练习页切换后重建正确页面。
- 登录页删去几何插画、按学科假进度条和灰底统计卡，改为「字标 + 单句标题 + 细分隔线 + 一行题库事实」；表单增加主题入口，勾选框新增 `Card.TCheckbutton` 消除深色底块，长文案增加 wraplength，窗体宽度按实测文本自适应（高 DPI 不裁切）。
- 首页**保持原 V2 四卡布局不变**（本轮只重设计登录页）。曾在同一次改造中尝试过极简首页，按用户要求已从备份恢复；恢复时把原 `home()` 的冻结色引用改为 `T.<TOKEN>` 以适配双主题，删除仅供极简版使用的 `_soft_card()`，并给「最近学习」空状态文案补 `wraplength`，避免默认英文下文字被裁切。深色进度轨道令牌由 `#161616` 改为可见的 `#343940`。
- `en.json` 补齐外观/深色/浅色/主题说明 4 条词条；3 处测试断言改为语言无关（从词条推导期望文本），验证默认英文下 84 项回归全部通过。
- `DESIGN.md` v2.2 同步双主题调色板并把简约规则限定在登录页；README 更新主题/默认语言说明、测试数量 54 → 84 与 `py -3` 运行命令。视觉对照截图见 `.workbuddy-ai/preview/`（不纳入版本库）。
- 恢复后复验：`py -3 -m py_compile learning_platform/*.py` 通过，`py -3 -m unittest discover -s tests` 84 项全通过；深浅两套首页截图重新采集。
