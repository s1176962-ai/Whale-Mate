# Quiz Battles / 答题对战

Current rules: 2026-11-21. This is the current battle guide. Superseded implementation notes are preserved in [the history archive](archive/BATTLE_HISTORY_20261121.md); changes are recorded in [CHANGELOG.md](CHANGELOG.md).

## English

### Setup and augments

- Choose Public or My bank, subject, topic, and 3/5/10 questions or ∞. Guests can use public questions; personal banks require an account.
- Choose Beginner/Normal/Hard/Hell, initial HP of 100/200/300/500/1,000, and Local or API.
- Question difficulty is sampled with easy/medium/hard weights of 70/25/5, 40/45/15, 15/45/40, or 5/25/70 respectively. Empty buckets redistribute their weight. Sampling is without replacement within each deck.
- Before the match, pick one of three distinct augments sampled without replacement using their configured weights. Rarities are random and may repeat within a hand. After three normal drafts without a Demon, the fourth guarantees one; any Demon appearance resets the counter. Opening a valid draft counts once, regardless of the card selected. Progress persists per account (guests are separate). The optional Demo draft guarantees a Demon without reading or changing normal pity progress, and defaults off whenever setup opens. The chosen effect lasts the match.

### Timing, scores and damage

Both sides receive the same question. Base time depends on question difficulty:

| Question difficulty | Base time | Speed thresholds for +50/+40/+30/+20/+10 |
| --- | --- | --- |
| easy | 25s | 4/8/12/17/25s |
| medium | 30s | 5/10/15/20/30s |
| hard | 45s | 8/15/23/30/45s |

A timely correct answer earns 100 base points plus speed points and any augment effects. Wrong or late answers earn no correctness or speed points and no correctness-dependent augment rewards. The lower round score loses HP equal to the score difference, bounded at zero. Defensive/offensive augments may alter this result.

Time Sandglass adds 8 seconds to the player's clock. Demonic Pact halves the player's clock and triples the total score; it does not multiply damage directly. Player speed thresholds use the player's adjusted clock; the opponent keeps the base question clock. Displayed damage belongs to the receiving side; the two health bars and score panels are mirrored.

### Reveal, pause and ending a match

- During answering and waiting for the opponent, pause and End match are unavailable. Both answers are revealed together.
- A correct player answer starts an approximately three-second automatic transition. ⏸ or Space pauses it; ▶ or Space resumes the remaining transition time.
- A wrong or timed-out player answer pauses automatically, including the last question or a knockout. The explanation remains available until the player resumes or ends the match.
- A caption identifies answering, waiting, automatic transition, manual pause, mistake pause, or an invalid round, with the applicable Space action.
- In finite mode, question exhaustion or zero HP leads to normal results. In infinite mode, exhausted decks reshuffle while both sides have HP; the question counter continues across decks.
- In infinite mode, **End match** becomes available after a settled round. It also works during review pauses. If both sides still have HP, the result is marked **Match ended early**, showing only settled rounds, accumulated scores and remaining HP. It counts neither as a victory/defeat nor a completed match, and cannot grant completion/victory badges. Earned question/streak badges and best statistics may still be recorded.
- If the revealed round already depleted HP, End match opens the normal result instead of converting the knockout into an early finish. Settlement is idempotent and cancels pending automatic transitions.
- Leaving through navigation is separate from End match and does not create a completed result. Unfinished sessions cannot be restored after restart.

### Opponents and API failures

Local is a labelled probability simulation: accuracy targets are 50%/72%/88%/97%, with simulated delays of 12–24/8–18/4–12/2–7 seconds. These are long-run probabilities, not guaranteed individual outcomes. API levels guide behaviour and simulated timing, not fixed accuracy.

API decisions are bound to the question ID, option, time and concise educational summaries. UI stages are activity indicators, not live internal reasoning. Choices and summaries remain hidden until reveal. There is no second request inventing a retrospective rationale.

API input includes question text, options and labelled local images, never the answer key or reference explanation. Supported images are PNG/JPEG/GIF/WebP, at most 8 MiB each and 16 MiB total, within the project directory. Official DeepSeek image requests use `deepseek-flash`; custom services require a compatible model. Structured output is limited to 800 tokens. Model answers and summaries can be wrong.

Failed, invalid or late responses void the round: no score, HP loss, or streak change. ▶ or Space retries it. Infinite matches with previously settled rounds may also end; a match with no settled rounds cannot be settled early. No silent Local fallback occurs.

### Achievements, skins and persistence

Accounts own achievement files under `profiles/<uuid>/achievements.json`; guests do not persist achievements. Natural results update completed-match/win statistics and eligible badges. Early finishes follow the restrictions above. Battle scores currently remain separate from normal quiz history, daily goals and the mistake notebook.

The home mascot's shirt button opens a separate wardrobe. Home, login and each opponent level have independent skin choices. Battle defaults follow difficulty (Hell uses the Hell pack); manual choices override that rule. Missing images fall back to defaults. Skin preferences are local to the installation, not account-specific. Settings retains the achievement-reset action.

## 中文

### 配置与海克斯

题库可选公共或我的，随后选择科目、主题、3/5/10 题或 ∞；个人题库需登录。对手等级为入门、普通、困难、地狱，初始血量为 100/200/300/500/1000，模式为 Local 或 API。题目按等级加权抽取 easy/medium/hard，权重分别为 70/25/5、40/45/15、15/45/40、5/25/70；缺桶时重新分配权重，每轮牌堆内不放回抽题。

开局按卡牌已有权重不放回抽三张不同强化，三选一后整局生效。稀有度不固定，可同档多张，连续三次普通抽卡未出魔王则第四次必出，出现即重置；按实际发牌次数计数，账号隔离并持久化。设置中的“演示抽卡”必含魔王，不影响普通保底，重新打开设置默认关闭。

### 计时、计分与伤害

双方同题。基础窗口由题目难度决定：easy 25 秒、medium 30 秒、hard 45 秒。速度分 +50/+40/+30/+20/+10 的阈值见上表。时限内答对基础 100 分，再加速度分与强化效果；答错或超时无正确分、速度分及依赖正确状态的强化奖励。低分方扣除双方分差，最低为零，强化可进一步改变伤害结果。

时间沙漏给玩家增加 8 秒；魔王契约使玩家时限减半、总得分乘三，不是伤害直接乘三。玩家速度分按调整后的窗口计算，对手保留基础窗口。左右血条、计分面板镜像，伤害显示在受击一侧。

### 揭晓、暂停与主动结算

- 作答和等待对手期间不能暂停或主动结算，双方完成后统一揭晓。
- 玩家答对后约三秒自动进入下一题或结果页；⏸ / 空格暂停，▶ / 空格恢复剩余等待时间。
- 玩家答错或超时自动暂停，包括最后一题和击倒回合，保留解析供查看。
- 按钮旁说明当前是答题、等待对手、自动推进、手动暂停、答错暂停还是本题作废，并提示空格操作。
- 有限模式题尽或血量归零自然结束；无限模式双方存活时题尽重洗，题号跨牌堆累计。
- 无限模式在每题结算后启用“结束并结算”，暂停时也可操作。双方仍存活时标记“主动结束”，显示已结算题数、累计得分和剩余血量；不计胜负或完成场次，不授予通关、获胜类成就，已达成的单题、连击成就及最佳统计仍可保存。
- 当前回合已经造成血量归零时，点击结束直接进入正常胜负结算。重复操作不会重复结算，待执行的自动进题任务会取消。
- 导航离开与主动结算不同，不产生完整结果；目前不支持重启后恢复未完成对战。

### 对手、异常与数据边界

Local 明确标记为概率模拟，四档正确率目标为 50%/72%/88%/97%，模拟用时为 12–24/8–18/4–12/2–7 秒；单局不保证命中目标比例。API 难度约束行为和模拟等待，不保证固定正确率。活动提示不是模型内部推理过程；揭晓展示同一份已保存决策摘要与独立题库解析，不追加编造解题理由的请求。

API 可发送题干、选项及标记过的本地图片，不发送答案或解析。图片限制、模型选择、输出限制与英文部分一致。错误、非法或迟到响应使该轮作废，不计分、不扣血、回滚连击变更，▶ / 空格重试，不悄悄切换 Local。无限模式已有结算回合时也可结束；零结算回合不能主动结算。

成就按账号隔离，访客不保存；对战目前不计入普通练习历史、每日目标或错题本。首页吉祥物旁衣服图标打开独立换肤页，首页、登录页和各对手等级分别配置；对战默认跟随难度，缺图回退，偏好为本机共用。设置页保留成就重置。
