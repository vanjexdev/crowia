import math
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen, QCursor


_STATE_COLORS = {
    "idle":      ("#3a9ee0", "#0d2a4a"),
    "listening": ("#88c93a", "#2a4a0d"),
    "speaking":  ("#58d8e8", "#0d3a44"),
    "thinking":  ("#e8c33a", "#4a3a0d"),
    "error":     ("#e05050", "#4a0d0d"),
    "success":   ("#88c93a", "#2a4a0d"),
}

_ORB_SIZE = 110


class FloatingOrb(QWidget):
    """Floating always-on-top orb. Shows Giselo state when main window is minimized."""

    def __init__(self, main_window, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(_ORB_SIZE, _ORB_SIZE)

        self._main = main_window
        self._state = "idle"
        self._phase = 0.0
        self._drag_pos: QPoint | None = None

        self._rings: list[float] = []
        self._ring_timer = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

        self._place_default()

    def set_state(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        if state in ("listening", "speaking"):
            self._rings.clear()
            self._ring_timer = 0

    def _tick(self) -> None:
        self._phase = (self._phase + 0.06) % (2 * math.pi)
        if self._state in ("listening", "speaking"):
            interval = 18 if self._state == "speaking" else 30
            self._ring_timer += 1
            if self._ring_timer >= interval:
                self._rings.append(0.0)
                self._ring_timer = 0
        speed = 0.025 if self._state == "speaking" else 0.016
        self._rings = [r + speed for r in self._rings if r < 1.0]
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        r = min(w, h) / 2.0 - 12
        c1_hex, c2_hex = _STATE_COLORS.get(self._state, _STATE_COLORS["idle"])
        c1 = QColor(c1_hex)
        c2 = QColor(c2_hex)
        self._draw_rings(painter, cx, cy, r, c1)
        self._draw_glow(painter, cx, cy, r, c1)
        self._draw_sphere(painter, cx, cy, r, c1, c2)
        self._draw_highlight(painter, cx, cy, r)
        if self._state == "thinking":
            self._draw_arc(painter, cx, cy, r, c1)
        painter.end()

    def _draw_rings(self, p, cx, cy, r, c1) -> None:
        for age in self._rings:
            ring_r = r + age * 38
            alpha = int(200 * (1.0 - age))
            pen = QPen(QColor(c1.red(), c1.green(), c1.blue(), alpha))
            pen.setWidthF(1.5)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2))

    def _draw_glow(self, p, cx, cy, r, c1) -> None:
        pulse = 0.82 + 0.18 * math.sin(self._phase * 1.8)
        gr = r * 1.55 * pulse
        glow = QRadialGradient(cx, cy, gr)
        glow.setColorAt(0.0, QColor(c1.red(), c1.green(), c1.blue(), 55))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(cx - gr, cy - gr, gr * 2, gr * 2))

    def _draw_sphere(self, p, cx, cy, r, c1, c2) -> None:
        breath = 0.96 + 0.04 * math.sin(self._phase)
        sr = r * breath
        grad = QRadialGradient(cx - sr * 0.28, cy - sr * 0.28, sr * 1.2)
        grad.setColorAt(0.00, QColor(255, 255, 255, 55))
        grad.setColorAt(0.30, c1)
        grad.setColorAt(0.72, c2)
        grad.setColorAt(1.00, QColor(0, 0, 0, 210))
        p.setBrush(grad)
        p.setPen(QPen(QColor(255, 255, 255, 25), 1))
        p.drawEllipse(QRectF(cx - sr, cy - sr, sr * 2, sr * 2))

    def _draw_highlight(self, p, cx, cy, r) -> None:
        hr = r * 0.33
        hx, hy = cx - r * 0.22, cy - r * 0.30
        hi = QRadialGradient(hx, hy, hr)
        hi.setColorAt(0.0, QColor(255, 255, 255, 120))
        hi.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(hi)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(hx - hr, hy - hr, hr * 2, hr * 2))

    def _draw_arc(self, p, cx, cy, r, c1) -> None:
        pen = QPen(c1, 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        arc_r = r * 0.68
        start = int(math.degrees(self._phase * 2) * 16) % (360 * 16)
        p.drawArc(QRectF(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2), start, 100 * 16)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.windowHandle()
            if handle:
                handle.startSystemMove()
            else:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _event) -> None:
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._main.showNormal()
            self._main.raise_()
            self._main.activateWindow()

    def contextMenuEvent(self, _event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #0f1a2e; color: #cfd6e6;
                    border: 1px solid rgba(93,107,133,0.5);
                    font-family: 'JetBrains Mono', monospace; font-size: 10px; }
            QMenu::item { padding: 5px 14px; }
            QMenu::item:selected { background: rgba(136,201,58,0.15); color: #88c93a; }
        """)
        act_show = menu.addAction("◈  Mostrar Giselo")
        act_hide = menu.addAction("✕  Ocultar orbe")
        chosen = menu.exec(QCursor.pos())
        if chosen == act_show:
            self._main.showNormal()
            self._main.raise_()
            self._main.activateWindow()
        elif chosen == act_hide:
            self.hide()

    def _place_default(self) -> None:
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.move(geom.right() - _ORB_SIZE - 24, geom.bottom() - _ORB_SIZE - 24)
