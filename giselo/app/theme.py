from PyQt6.QtGui import QColor

# ── Design tokens ──────────────────────────────────────────────────────────────

BG           = "#0a1020"
BG_GRID      = "rgba(200,220,255,0.04)"
PANEL        = "#0f1a2e"
CHROME       = "#080e1c"
RAIL         = "#0b1228"

INK          = "#cfd6e6"
MUTE         = "#5d6b85"

LIME         = "#88c93a"
CYAN         = "#3a9ee0"
YELLOW       = "#e8c33a"
ORANGE       = "#e07a3a"
RED          = "#cc4040"

ACCENT_DEFAULT = LIME

FONT_UI   = "Inter, Geist Sans, Segoe UI, system-ui, sans-serif"
FONT_MONO = "JetBrains Mono, Consolas, monospace"

BORDER_PX    = "1.5px"
RADIUS_CHIP  = "3px"
RADIUS_PANEL = "4px"
RADIUS_CARD  = "6px"


def qcolor(hex_str: str) -> QColor:
    return QColor(hex_str)


def accent_rgb(hex_str: str = ACCENT_DEFAULT) -> tuple[int, int, int]:
    c = QColor(hex_str)
    return c.red(), c.green(), c.blue()


# ── QSS ───────────────────────────────────────────────────────────────────────

def build_qss(accent: str = ACCENT_DEFAULT) -> str:
    ar, ag, ab = accent_rgb(accent)
    return f"""
/* ── Global ── */
QMainWindow, QWidget {{
    background: {BG};
    color: {INK};
    font-family: Inter, 'Geist Sans', 'Segoe UI', system-ui, sans-serif;
    font-size: 12px;
}}

QScrollBar:vertical {{
    background: {PANEL};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {MUTE};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Title bar ── */
#title-bar {{
    background: {CHROME};
    border-bottom: 1px solid {INK};
    min-height: 30px;
    max-height: 30px;
}}
#title-label {{
    color: {INK};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 2px;
}}
#title-hint {{
    color: {MUTE};
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
}}
#traffic-close  {{ background: {RED};    border-radius: 5px; min-width:10px; max-width:10px; min-height:10px; max-height:10px; border: 1px solid rgba(255,255,255,0.15); }}
#traffic-min    {{ background: {YELLOW}; border-radius: 5px; min-width:10px; max-width:10px; min-height:10px; max-height:10px; border: 1px solid rgba(255,255,255,0.15); }}
#traffic-max    {{ background: {LIME};   border-radius: 5px; min-width:10px; max-width:10px; min-height:10px; max-height:10px; border: 1px solid rgba(255,255,255,0.15); }}

/* ── Tab dock ── */
#tab-dock {{
    background: {CHROME};
    border-bottom: 1px solid {INK};
    min-height: 34px;
    max-height: 34px;
}}
QPushButton[tabButton="true"] {{
    background: transparent;
    color: {MUTE};
    border: 1px solid {INK};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 4px 10px;
    font-size: 11px;
    font-family: Inter, sans-serif;
}}
QPushButton[tabButton="true"]:hover {{
    color: {INK};
    background: rgba(255,255,255,0.04);
}}
QPushButton[tabActive="true"] {{
    background: {PANEL};
    color: {INK};
    border: 1px solid {INK};
    border-bottom: 1px solid {PANEL};
}}
QPushButton[tabAdd="true"] {{
    background: transparent;
    color: {MUTE};
    border: 1px dashed {MUTE};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 4px 10px;
    font-size: 11px;
}}
QPushButton[tabAdd="true"]:hover {{
    color: {INK};
}}

/* ── Rails ── */
#rail-left, #rail-right {{
    background: {RAIL};
    min-width: 44px;
    max-width: 44px;
}}
QPushButton[railBtn="true"] {{
    background: transparent;
    color: {INK};
    border: 1px solid rgba(93,107,133,0.5);
    border-radius: {RADIUS_CARD};
    margin: 1px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    font-size: 14px;
    padding: 0;
}}
QPushButton[railBtn="true"]:hover {{
    background: rgba(255,255,255,0.06);
    border: 1px solid {INK};
}}
QPushButton[railActive="true"] {{
    border: 1px solid {accent};
    background: rgba({ar},{ag},{ab},0.12);
    color: {accent};
}}

/* ── Drawer ── */
#drawer {{
    background: {PANEL};
    border-right: 1px solid {INK};
}}
#drawer-header {{
    border-bottom: 1px dashed {accent};
    padding: 8px 12px;
}}
#drawer-title {{
    color: {accent};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    font-family: Inter, sans-serif;
}}
QPushButton#drawer-close {{
    background: transparent;
    color: {MUTE};
    border: none;
    font-size: 14px;
    padding: 0;
    min-width: 20px;
    max-width: 20px;
}}
QPushButton#drawer-close:hover {{ color: {INK}; }}

/* ── Center / core ── */
#center-widget {{
    background: transparent;
}}

/* ── Chat preview cards ── */
#chat-preview {{
    background: transparent;
    min-height: 80px;
    max-height: 80px;
}}
QFrame[chatCard="true"] {{
    background: {PANEL};
    border: 1px solid {INK};
    border-radius: {RADIUS_CARD};
}}
QLabel[cardAuthor="true"] {{
    font-size: 11px;
    font-weight: 700;
}}
QLabel[cardTime="true"] {{
    color: {MUTE};
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
}}
QLabel[cardBody="true"] {{
    color: {INK};
    font-size: 11px;
}}

/* ── Input bar ── */
#input-bar {{
    background: {PANEL};
    border: 2px solid {INK};
    border-radius: {RADIUS_CARD};
    margin: 0 12px 8px 12px;
}}
QPlainTextEdit#input-field {{
    background: transparent;
    color: {INK};
    border: none;
    font-size: 12px;
    padding: 8px;
    selection-background-color: rgba({ar},{ag},{ab},0.30);
}}
QPlainTextEdit#input-field::placeholder {{
    color: {MUTE};
}}
QPushButton[inputBtn="true"] {{
    background: transparent;
    color: {INK};
    border: 1px solid {INK};
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
}}
QPushButton[inputBtn="true"]:hover {{
    background: rgba(255,255,255,0.06);
}}
QPushButton[inputBtnAccent="true"] {{
    color: {accent};
    border: 1px solid {accent};
    background: rgba({ar},{ag},{ab},0.12);
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
}}
QPushButton[inputBtnAccent="true"]:hover {{
    background: rgba({ar},{ag},{ab},0.22);
}}
QPushButton[inputBtnCam="true"] {{
    color: {LIME};
    border: 1px solid {LIME};
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    background: transparent;
}}
QPushButton[inputBtnVoz="true"] {{
    color: {CYAN};
    border: 1px solid {CYAN};
    background: rgba(58,158,224,0.12);
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
}}

/* ── Status bar ── */
#status-bar {{
    background: {CHROME};
    border-top: 1px solid {INK};
    min-height: 22px;
    max-height: 22px;
}}
QLabel[statusItem="true"] {{
    color: {MUTE};
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    padding: 0 4px;
}}
QLabel[statusOnline="true"] {{
    color: {LIME};
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    padding: 0 4px;
}}
QLabel[statusVersion="true"] {{
    color: {MUTE};
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    padding: 0 6px;
}}
"""
