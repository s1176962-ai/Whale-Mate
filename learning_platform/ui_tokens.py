"""Runtime-switchable design tokens (compatibility surface).

The values themselves live in :mod:`learning_platform.tokens` -- this module is
only a re-export plus the runtime colour rebind that the existing GUI relies on.
Import it as ``from . import ui_tokens as T`` and read colours as ``T.BG`` at
render time; ``set_theme()`` rebinds every colour in this module's globals.
"""

from . import tokens as _tokens
from .tokens import (
    CARD_PAD,
    CARD_WIDTH,
    CONTENT_MAX,
    CONTENT_MIN,
    CONTROL_H,
    DURATION_FAST_MS,
    FIELD_GAP,
    FOCUS_RING,
    FONT,
    FONT_FALLBACK,
    FONT_MONO,
    GROUP_GAP,
    HAIRLINE,
    HIT,
    ICON,
    LINE_HEIGHT,
    NAV_INDICATOR,
    NAV_W,
    PAGE_PAD,
    PROGRESS_H,
    PX_BODY,
    PX_BODY_LARGE,
    PX_CAPTION,
    PX_TITLE,
    RADIUS_AVATAR,
    RADIUS_CARD,
    RADIUS_CHIP,
    RADIUS_CONTROL,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    ROW_H,
    SHADOW_BLUR_FAR,
    SHADOW_OFFSET_FAR,
    SHADOW_OFFSET_NEAR,
    SHADOW_RGBA_FAR,
    SHADOW_RGBA_NEAR,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_5,
    SPACE_6,
    SPACE_7,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    SPLIT_WIDE,
    THEMES,
    TOPBAR_H,
    TYPE_BODY,
    TYPE_BODY_LARGE,
    TYPE_BUTTON,
    TYPE_CAPTION,
    TYPE_CARD,
    TYPE_FOOT,
    TYPE_HEADING,
    TYPE_HERO,
    TYPE_HINT,
    TYPE_KICKER,
    TYPE_LABEL,
    TYPE_MARK,
    TYPE_NUM,
    TYPE_QUESTION,
    TYPE_TITLE,
    TYPE_TOOL,
    WINDOW_MIN,
    WINDOW_SIZE,
    font_at,
    mix,
    px,
    scale,
    set_scale,
)

# Colour tokens are injected into this module's globals at runtime by
# set_theme()/globals().update(palette()). Static type checkers cannot see that,
# so declare them here as bare annotations: at runtime these are erased to
# __annotations__ (no value assigned), and set_theme() still supplies the real
# colours. This keeps ``T.BG``-style reads type-clean under Pylance/pyright.
# Keep this list in sync with tokens.palette() (tested in test_ui_tokens.py).
ACCENT: str
AI_INPUT_BG: str
AI_INPUT_EDGE: str
AI_REPLY_BG: str
AI_REPLY_EDGE: str
BG: str
BORDER: str
BORDER_CONTROL: str
BORDER_LIGHT: str
BUTTON_FILL: str
BUTTON_INK: str
CHECK_BORDER: str
CHECK_MARK: str
COLOR_ACCENT: str
COLOR_BORDER: str
COLOR_BUTTON: str
COLOR_BUTTON_INK: str
COLOR_MUTED: str
COLOR_PAGE: str
COLOR_PRIMARY: str
COLOR_PRIMARY_DARK: str
COLOR_RAISED: str
COLOR_SURFACE: str
COLOR_TEXT: str
DISABLED_FILL: str
DISABLED_INK: str
ERROR: str
ERROR_BG: str
FOCUS_GLOW: str
HOVER: str
INFO: str
INFO_BG: str
MUTED: str
NAV: str
NAV_BG: str
NAV_SELECTED: str
ON_PRIMARY: str
PAGE: str
PRESSED: str
PRIMARY: str
PRIMARY_ACTIVE: str
PRIMARY_DISABLED: str
PRIMARY_HOVER: str
PRIMARY_SOFT: str
RAISED: str
SCROLL_ACTIVE: str
SCROLL_HOVER: str
SCROLL_THUMB: str
SEGMENT_SELECTED: str
SEGMENT_TRACK: str
SELECTED_BG: str
SHADOW: str
SHADOW_CARD: str
SHADOW_FAR: str
SHADOW_NEAR: str
SKY: str
SUCCESS_BG: str
SUCCESS_FG: str
SURFACE: str
TEXT: str
TEXT_MUTED: str
TEXT_SECONDARY: str
TRACK: str
WARNING: str
WARNING_BG: str


def set_theme(name):
    """Rebind every colour token in this module and return the applied key."""
    applied = _tokens.set_theme(name)
    globals().update(_tokens.palette())
    return applied


def theme_name():
    return _tokens.theme_name()


def palette():
    return _tokens.palette()


set_theme("dark")
