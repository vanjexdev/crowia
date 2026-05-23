"""Edge-resize for frameless windows — Wayland + X11 compatible via startSystemResize."""
from PyQt6.QtCore import QObject, QEvent, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication

_EDGE_PX = 6

# Qt.Edge values: Top=1, Bottom=2, Left=4, Right=8
_CURSOR_MAP: dict[int, Qt.CursorShape] = {
    5:  Qt.CursorShape.SizeFDiagCursor,   # Top | Left
    9:  Qt.CursorShape.SizeBDiagCursor,   # Top | Right
    6:  Qt.CursorShape.SizeBDiagCursor,   # Bottom | Left
    10: Qt.CursorShape.SizeFDiagCursor,   # Bottom | Right
    1:  Qt.CursorShape.SizeVerCursor,     # Top
    2:  Qt.CursorShape.SizeVerCursor,     # Bottom
    4:  Qt.CursorShape.SizeHorCursor,     # Left
    8:  Qt.CursorShape.SizeHorCursor,     # Right
}


def _detect_edges(x: int, y: int, w: int, h: int) -> Qt.Edge:
    e = _EDGE_PX
    edges = Qt.Edge(0)
    if x < e:       edges |= Qt.Edge.LeftEdge
    elif x > w - e: edges |= Qt.Edge.RightEdge
    if y < e:       edges |= Qt.Edge.TopEdge
    elif y > h - e: edges |= Qt.Edge.BottomEdge
    return edges


class ResizeFilter(QObject):
    """App-level event filter that enables edge-resize on a frameless QMainWindow."""

    def __init__(self, window):
        super().__init__(window)
        self._win = window

    def install(self) -> None:
        QApplication.instance().installEventFilter(self)

    def uninstall(self) -> None:
        QApplication.instance().removeEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        t = event.type()

        if t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            local = self._win.mapFromGlobal(QCursor.pos())
            if self._win.rect().contains(local):
                edges = _detect_edges(local.x(), local.y(), self._win.width(), self._win.height())
                if edges:
                    handle = self._win.windowHandle()
                    if handle:
                        handle.startSystemResize(edges)
                        return True

        elif t == QEvent.Type.MouseMove:
            if not event.buttons():
                local = self._win.mapFromGlobal(QCursor.pos())
                if self._win.rect().contains(local):
                    edges = _detect_edges(local.x(), local.y(), self._win.width(), self._win.height())
                    cursor = _CURSOR_MAP.get(edges.value if hasattr(edges, 'value') else int(edges))
                    if cursor:
                        self._win.setCursor(cursor)
                    else:
                        self._win.unsetCursor()

        return False
