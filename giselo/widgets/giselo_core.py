import math
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtProperty
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont, QRadialGradient, QBrush

from giselo.app.theme import LIME, CYAN, MUTE, INK, BG, accent_rgb

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

STATE_ASSETS = {
    "idle":     "normal.png",
    "thinking": "thinking.png",
    "speaking": "open.png",
    "success":  "like.png",
    "error":    "closet.png",
    "off":      "closet.png",
}

NUM_RINGS   = 5
NUM_BARS    = 26
RING_OPACITIES = [0.45, 0.36, 0.27, 0.20, 0.13]
TICK_COUNT  = 24


class GiseloCore(QWidget):
    """Center widget: voice rings + Giselo sprite + spectrum bars + status pill."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("center-widget")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(300, 300)

        self._state      = "idle"
        self._accent     = QColor(LIME)
        self._level      = 0.0          # 0.0 – 1.0 audio level
        self._ring_phase = 0.0          # rotation phase for ring dashes
        self._bars       = [0.0] * NUM_BARS
        self._pixmaps: dict[str, QPixmap] = {}
        self._load_pixmaps()

        # Status pill text
        self._pill_text  = "● ESCUCHANDO · LVL 0%"
        self._pill_visible = True

        # Animation timer (30 fps)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, state: str) -> None:
        if state in STATE_ASSETS:
            self._state = state
            self.update()

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, level))
        pct = int(self._level * 100)
        self._pill_text = f"● ESCUCHANDO · LVL {pct}%"
        self.update()

    def set_bars(self, bars: list[float]) -> None:
        self._bars = bars[:NUM_BARS] + [0.0] * max(0, NUM_BARS - len(bars))
        self.update()

    def set_pill_text(self, text: str) -> None:
        self._pill_text = text
        self.update()

    def set_accent(self, color: QColor) -> None:
        self._accent = color
        self.update()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _load_pixmaps(self) -> None:
        for state, fname in STATE_ASSETS.items():
            path = os.path.join(ASSETS_DIR, fname)
            if os.path.exists(path):
                self._pixmaps[state] = QPixmap(path)

    def _tick(self) -> None:
        self._ring_phase = (self._ring_phase + 0.5) % 360
        # Idle bar animation (subtle noise)
        if self._state == "idle":
            import random
            self._bars = [max(0.05, min(1.0, b + random.uniform(-0.05, 0.05))) for b in self._bars]
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2

        ring_size = min(W * 0.78, H * 0.55, 460)
        sprite_size = ring_size * 0.62

        self._draw_glow(painter, cx, cy, ring_size)
        self._draw_rings(painter, cx, cy, ring_size)
        self._draw_sprite(painter, cx, cy, sprite_size)
        self._draw_spectrum(painter, cx, cy, ring_size)
        self._draw_pill(painter, cx, cy, ring_size)

        painter.end()

    def _draw_glow(self, painter: QPainter, cx: float, cy: float, ring_size: float) -> None:
        r = ring_size * 0.55
        grad = QRadialGradient(QPointF(cx, cy), r)
        c = QColor(self._accent)
        c.setAlphaF(0.18)
        grad.setColorAt(0, c)
        c2 = QColor(self._accent)
        c2.setAlphaF(0.0)
        grad.setColorAt(1, c2)
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), r, r)

    def _draw_rings(self, painter: QPainter, cx: float, cy: float, ring_size: float) -> None:
        for i in range(NUM_RINGS):
            frac = (i + 1) / NUM_RINGS
            r    = ring_size * 0.5 * frac
            alpha = int(RING_OPACITIES[i] * 255)
            color = QColor(self._accent)
            color.setAlpha(alpha)

            pen = QPen(color)
            pen.setWidthF(1.5)

            # Alternate solid / dashed rings
            if i % 2 == 1:
                dash_len   = 8.0
                space_len  = 6.0
                # rotate dashes with phase
                pen.setDashPattern([dash_len, space_len])
                pen.setDashOffset(self._ring_phase * (i + 1) * 0.3)

            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r, r)

        # Tick marks on outer ring
        outer_r = ring_size * 0.5
        tick_r  = outer_r + 4
        tick_color = QColor(self._accent)
        tick_color.setAlpha(80)
        pen = QPen(tick_color)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        for k in range(TICK_COUNT):
            angle = math.radians(k * 360 / TICK_COUNT + self._ring_phase * 0.1)
            ix = cx + outer_r * math.cos(angle)
            iy = cy + outer_r * math.sin(angle)
            ox = cx + tick_r  * math.cos(angle)
            oy = cy + tick_r  * math.sin(angle)
            painter.drawLine(QPointF(ix, iy), QPointF(ox, oy))

    def _draw_sprite(self, painter: QPainter, cx: float, cy: float, sprite_size: float) -> None:
        px = self._pixmaps.get(self._state) or self._pixmaps.get("idle")
        if not px:
            return
        sz  = int(sprite_size)
        scaled = px.scaled(sz, sz, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
        x = int(cx - scaled.width()  / 2)
        y = int(cy - scaled.height() / 2)
        painter.drawPixmap(x, y, scaled)

    def _draw_spectrum(self, painter: QPainter, cx: float, cy: float, ring_size: float) -> None:
        bar_area_w = ring_size * 0.72
        bar_area_h = 36.0
        bar_w      = bar_area_w / (NUM_BARS * 1.6)
        gap        = bar_w * 0.6
        total_w    = NUM_BARS * (bar_w + gap) - gap
        x0         = cx - total_w / 2
        y_base     = cy + ring_size * 0.52

        for i, level in enumerate(self._bars):
            bar_h = max(3.0, level * bar_area_h)
            x     = x0 + i * (bar_w + gap)
            y     = y_base - bar_h

            color = QColor(self._accent)
            color.setAlphaF(0.55 + level * 0.45)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 1.5, 1.5)

    def _draw_pill(self, painter: QPainter, cx: float, cy: float, ring_size: float) -> None:
        if not self._pill_visible:
            return

        font = QFont("JetBrains Mono, monospace")
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)

        fm   = painter.fontMetrics()
        text = self._pill_text
        tw   = fm.horizontalAdvance(text)
        th   = fm.height()
        pad  = 8

        pill_w = tw + pad * 2
        pill_h = th + 6
        px     = cx - pill_w / 2
        py     = cy - ring_size * 0.52 - pill_h

        # Pill background
        bg = QColor(BG)
        bg.setAlpha(220)
        painter.setBrush(QBrush(bg))
        border = QColor(self._accent)
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(QRectF(px, py, pill_w, pill_h), 3, 3)

        # Pill text
        painter.setPen(QPen(self._accent))
        painter.drawText(QPointF(px + pad, py + th - 1), text)
