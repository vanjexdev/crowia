import math
import os
import time
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (QPainter, QPen, QColor, QPixmap, QFont,
                          QRadialGradient, QBrush, QLinearGradient)

from giselo.app.theme import LIME, MUTE, BG

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

STATE_ASSETS = {
    "idle":     "normal.png",
    "thinking": "thinking.png",
    "speaking": "open.png",
    "success":  "like.png",
    "error":    "closet.png",
    "off":      "closet.png",
}

NUM_RINGS    = 5
NUM_BARS     = 26
RING_OPACITIES = [0.45, 0.36, 0.27, 0.20, 0.13]
TICK_COUNT   = 24
FADE_STEPS   = 8          # ~250ms at 30fps
BREATH_SPEED = 0.012      # radians per tick → ~5s full cycle at 30fps


class GiseloCore(QWidget):
    """Center widget: voice rings + Giselo sprite (with crossfade) + spectrum + status pill."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("center-widget")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(300, 300)

        self._state       = "idle"
        self._prev_state  = "idle"
        self._fade_prog   = 1.0        # 0.0 = fully prev, 1.0 = fully current
        self._fade_step   = 0

        self._accent      = QColor(LIME)
        self._level       = 0.0
        self._ring_phase  = 0.0
        self._breath_phase = 0.0
        self._breath_scale = 1.0

        self._bars        = [0.08] * NUM_BARS

        self._pill_text   = "● ESCUCHANDO · LVL 0%"
        self._pill_glow   = 0.0       # 0.0–1.0 glow intensity for pill pulse

        self._pixmaps: dict[str, QPixmap] = {}
        self._load_pixmaps()

        # 30 fps timer
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, new_state: str) -> None:
        if new_state == self._state or new_state not in STATE_ASSETS:
            return
        self._prev_state = self._state
        self._state      = new_state
        self._fade_prog  = 0.0
        self._fade_step  = 0

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, level))
        pct = int(self._level * 100)
        self._pill_text = f"● ESCUCHANDO · LVL {pct}%"

    def set_bars(self, bars: list[float]) -> None:
        self._bars = (bars[:NUM_BARS] + [0.0] * NUM_BARS)[:NUM_BARS]

    def set_pill_text(self, text: str) -> None:
        self._pill_text = text

    def set_accent(self, color: QColor) -> None:
        self._accent = color

    # ── Tick ─────────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        # Ring rotation
        self._ring_phase = (self._ring_phase + 0.6) % 360.0

        # Crossfade progress
        if self._fade_prog < 1.0:
            self._fade_step += 1
            self._fade_prog = min(1.0, self._fade_step / FADE_STEPS)

        # Breathing (idle only)
        if self._state == "idle":
            self._breath_phase = (self._breath_phase + BREATH_SPEED) % (2 * math.pi)
            self._breath_scale = 1.0 + 0.012 * math.sin(self._breath_phase)
        else:
            self._breath_scale = 1.0

        # Spectrum idle shimmer
        if self._state == "idle":
            import random
            self._bars = [
                max(0.04, min(0.35, b + random.uniform(-0.04, 0.04)))
                for b in self._bars
            ]
        elif self._state == "speaking":
            # Bars driven by level with randomness
            import random
            self._bars = [
                max(0.1, min(1.0, self._level * random.uniform(0.6, 1.4)))
                for _ in self._bars
            ]

        # Pill glow pulse (sync with level)
        self._pill_glow = 0.5 + 0.5 * math.sin(time.monotonic() * 4.0) if self._level > 0.1 else 0.5

        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        W, H = self.width(), self.height()
        cx, cy = W / 2.0, H / 2.0

        ring_size  = min(W * 0.78, H * 0.55, 460.0)
        sprite_size = ring_size * 0.62

        self._draw_glow(painter, cx, cy, ring_size)
        self._draw_rings(painter, cx, cy, ring_size)
        self._draw_sprite(painter, cx, cy, sprite_size)
        self._draw_spectrum(painter, cx, cy, ring_size)
        self._draw_pill(painter, cx, cy, ring_size)

        painter.end()

    # ── Glow ──────────────────────────────────────────────────────────────────

    def _draw_glow(self, p: QPainter, cx: float, cy: float, ring_size: float) -> None:
        r = ring_size * 0.52
        grad = QRadialGradient(QPointF(cx, cy), r)
        c0 = QColor(self._accent)
        c0.setAlphaF(0.20 + self._level * 0.10)
        grad.setColorAt(0.0, c0)
        c1 = QColor(self._accent)
        c1.setAlphaF(0.0)
        grad.setColorAt(1.0, c1)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r, r)

    # ── Rings ─────────────────────────────────────────────────────────────────

    def _draw_rings(self, p: QPainter, cx: float, cy: float, ring_size: float) -> None:
        # Rings pulse slightly with level when speaking
        pulse = 1.0 + (self._level * 0.04 if self._state == "speaking" else 0.0)

        for i in range(NUM_RINGS):
            frac  = (i + 1) / NUM_RINGS
            r     = ring_size * 0.5 * frac * pulse
            alpha = int(RING_OPACITIES[i] * 255)

            color = QColor(self._accent)
            color.setAlpha(alpha)
            pen = QPen(color)
            pen.setWidthF(1.5)

            if i % 2 == 1:
                pen.setDashPattern([8.0, 6.0])
                # Each dashed ring rotates at different speed
                pen.setDashOffset(self._ring_phase * (i + 1) * 0.25)

            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r, r)

        # Tick marks on outer ring
        outer_r = ring_size * 0.5 * pulse
        tick_r  = outer_r + 5.0
        tick_color = QColor(self._accent)
        tick_color.setAlpha(70)
        pen = QPen(tick_color, 1.0)
        p.setPen(pen)
        for k in range(TICK_COUNT):
            angle = math.radians(k * 360.0 / TICK_COUNT + self._ring_phase * 0.08)
            ix = cx + outer_r * math.cos(angle)
            iy = cy + outer_r * math.sin(angle)
            ox = cx + tick_r  * math.cos(angle)
            oy = cy + tick_r  * math.sin(angle)
            p.drawLine(QPointF(ix, iy), QPointF(ox, oy))

    # ── Sprite with crossfade + breathing ────────────────────────────────────

    def _draw_sprite(self, p: QPainter, cx: float, cy: float, sprite_size: float) -> None:
        scaled_size = sprite_size * self._breath_scale

        if self._fade_prog < 1.0:
            # Draw previous state fading out
            p.setOpacity(1.0 - self._fade_prog)
            self._blit(p, cx, cy, scaled_size, self._prev_state)
            # Draw current state fading in
            p.setOpacity(self._fade_prog)
            self._blit(p, cx, cy, scaled_size, self._state)
            p.setOpacity(1.0)
        else:
            self._blit(p, cx, cy, scaled_size, self._state)

    def _blit(self, p: QPainter, cx: float, cy: float, size: float, state: str) -> None:
        px = self._pixmaps.get(state) or self._pixmaps.get("idle")
        if not px:
            return
        sz = int(size)
        scaled = px.scaled(sz, sz,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
        x = int(cx - scaled.width()  / 2)
        y = int(cy - scaled.height() / 2)
        p.drawPixmap(x, y, scaled)

    # ── Spectrum ──────────────────────────────────────────────────────────────

    def _draw_spectrum(self, p: QPainter, cx: float, cy: float, ring_size: float) -> None:
        area_w = ring_size * 0.70
        max_h  = 38.0
        min_h  = 3.0
        bar_w  = area_w / (NUM_BARS * 1.55)
        gap    = bar_w * 0.55
        total  = NUM_BARS * (bar_w + gap) - gap
        x0     = cx - total / 2.0
        y_base = cy + ring_size * 0.53

        for i, lvl in enumerate(self._bars):
            bar_h = min_h + lvl * (max_h - min_h)
            x     = x0 + i * (bar_w + gap)
            y     = y_base - bar_h

            # Color gradient: center bars brighter
            center_dist = abs(i - NUM_BARS / 2) / (NUM_BARS / 2)
            alpha = 0.75 - center_dist * 0.30
            color = QColor(self._accent)
            color.setAlphaF(alpha)

            p.setBrush(QBrush(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 1.5, 1.5)

    # ── Status pill ───────────────────────────────────────────────────────────

    def _draw_pill(self, p: QPainter, cx: float, cy: float, ring_size: float) -> None:
        font = QFont("JetBrains Mono")
        font.setPointSize(8)
        p.setFont(font)
        fm   = p.fontMetrics()
        text = self._pill_text
        tw   = fm.horizontalAdvance(text)
        th   = fm.height()
        pad  = 10

        pill_w = tw + pad * 2
        pill_h = th + 8
        px_    = cx - pill_w / 2
        py_    = cy - ring_size * 0.53 - pill_h - 2

        # Glow behind pill (pulses with level)
        glow_r = max(pill_w, pill_h) * 0.8
        glow_c = QColor(self._accent)
        glow_c.setAlphaF(0.12 * self._pill_glow)
        grad = QRadialGradient(QPointF(cx, py_ + pill_h / 2), glow_r)
        grad.setColorAt(0, glow_c)
        glow_c2 = QColor(self._accent)
        glow_c2.setAlphaF(0.0)
        grad.setColorAt(1, glow_c2)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, py_ + pill_h / 2), glow_r, glow_r * 0.6)

        # Pill body
        bg = QColor(BG)
        bg.setAlpha(230)
        p.setBrush(QBrush(bg))
        border = QColor(self._accent)
        border.setAlphaF(0.7 + 0.3 * self._pill_glow)
        p.setPen(QPen(border, 1.0))
        p.drawRoundedRect(QRectF(px_, py_, pill_w, pill_h), 3, 3)

        # Pill text
        p.setPen(QPen(self._accent))
        p.drawText(QPointF(px_ + pad, py_ + th + 2), text)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_pixmaps(self) -> None:
        for state, fname in STATE_ASSETS.items():
            path = os.path.join(ASSETS_DIR, fname)
            if os.path.exists(path):
                self._pixmaps[state] = QPixmap(path)
