# Quiz App images

The resource paths below are relative to `assets/images/` at the repository root.

以下资源路径均相对于项目根目录的 `assets/images/`。

- `placeholder.png` — generic fallback when a path fails
- `subjects/` — soft colour blocks for English / Mathematics / Science
- `questions/` — put per-question art here as `{QUESTION_ID}.png`

Battle mascot art is organised as **swappable skin packs** under `assets/battle/skins/`:

```
assets/battle/skins/
├── skin_registry.json          # skin list + per-state file map
├── default/                    # standard blue/white mascot
│   └── {normal, thinking, correct, wrong, attack, attacked, die}.png
└── hell/                       # black/red gothic variant (hell difficulty)
    └── {normal, thinking, correct, wrong, attack, attacked, die}.png
```

Every skin provides the same 7 standalone transparent PNG states:

- `normal` — idle / general pose
- `thinking` — question being read
- `correct` / `wrong` — answer reaction
- `attack` — spraying water (player lost HP)
- `attacked` — hit by a hammer (opponent lost HP)
- `die` — knocked out (opponent HP reached 0)

`skin_registry.json` maps each skin id to its display names and file paths; `learning_platform/skins.py` resolves a `(skin, state)` pair to a path with automatic fallback (requested skin → default skin → legacy flat assets). Adding a skin = drop a folder with the 7 PNGs + one registry entry, no code change.

Legacy flat files remain in `assets/battle/` (`expressions.png`, `ai_assistant_*.png`) as fallbacks and for the home-page avatar; they are not used by the battle skin picker.

See [image matching guide](IMAGE_MATCHING.md) for the matching checklist. Question JSON still uses optional `question_image` and `option_images`.

对战吉祥物素材按**可换肤皮肤包**组织在 `assets/battle/skins/`：每个皮肤（`default` 默认蓝白 / `hell` 地狱黑红）都提供 `normal`（一般）、`thinking`（思考）、`correct`（答对）、`wrong`（答错）、`attack`（喷水）、`attacked`（被砸）、`die`（倒地）七张独立透明 PNG。`skin_registry.json` 声明皮肤清单与文件映射，`learning_platform/skins.py` 负责按 `(皮肤, 状态)` 解析路径并逐级回退。新增皮肤只需加一个含七张图的文件夹 + 一条注册表配置，无需改代码。`assets/battle/` 根目录的旧文件作为回退与首页头像保留。
