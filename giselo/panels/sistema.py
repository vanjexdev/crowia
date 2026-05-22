from PyQt6.QtWidgets import QLabel, QVBoxLayout, QProgressBar, QWidget, QHBoxLayout
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor
import psutil
from giselo.app.theme import LIME, CYAN, YELLOW, ORANGE, MUTE, INK


class _MetricRow(QWidget):
    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        self._lbl = QLabel(label)
        self._lbl.setFixedWidth(52)
        self._lbl.setStyleSheet(
            f"color: {MUTE}; font-family: 'JetBrains Mono', monospace; font-size: 10px;"
        )
        layout.addWidget(self._lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(93,107,133,0.25);
                border-radius: 3px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self._bar, stretch=1)

        self._val = QLabel("–")
        self._val.setFixedWidth(58)
        self._val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._val.setStyleSheet(
            f"color: {color}; font-family: 'JetBrains Mono', monospace; font-size: 10px;"
        )
        layout.addWidget(self._val)

    def update(self, pct: float, text: str) -> None:
        self._bar.setValue(int(pct))
        self._val.setText(text)


def build(layout: QVBoxLayout) -> None:
    cpu_row  = _MetricRow("CPU",   LIME)
    ram_row  = _MetricRow("RAM",   CYAN)
    gpu_row  = _MetricRow("GPU",   YELLOW)
    net_d    = _MetricRow("NET ↓", ORANGE)
    net_u    = _MetricRow("NET ↑", ORANGE)

    for w in (cpu_row, ram_row, gpu_row, net_d, net_u):
        layout.insertWidget(layout.count() - 1, w)

    _net_prev = {"bytes_recv": 0, "bytes_sent": 0}

    def _refresh():
        # CPU
        cpu = psutil.cpu_percent(interval=None)
        cpu_row.update(cpu, f"{cpu:.0f}%")

        # RAM
        mem  = psutil.virtual_memory()
        ram_pct = mem.percent
        ram_gb  = mem.used / 1024**3
        ram_row.update(ram_pct, f"{ram_gb:.1f}GB")

        # GPU (nvidia-smi via subprocess, optional)
        try:
            import subprocess
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu",
                 "--format=csv,noheader,nounits"],
                timeout=0.5, stderr=subprocess.DEVNULL
            ).decode().strip()
            g = float(out.split("\n")[0])
            gpu_row.update(g, f"{g:.0f}%")
        except Exception:
            gpu_row.update(0, "–")

        # NET
        net = psutil.net_io_counters()
        dr = (net.bytes_recv - _net_prev["bytes_recv"]) / 1024
        ds = (net.bytes_sent - _net_prev["bytes_sent"]) / 1024
        _net_prev["bytes_recv"] = net.bytes_recv
        _net_prev["bytes_sent"] = net.bytes_sent

        def _fmt(kb): return f"{kb:.0f}KB" if kb < 1024 else f"{kb/1024:.1f}MB"
        net_d.update(min(100, dr / 10), _fmt(dr))
        net_u.update(min(100, ds / 10), _fmt(ds))

    # Refresh every 2s; initial call now
    _refresh()
    timer = QTimer()
    timer.setInterval(2000)
    timer.timeout.connect(_refresh)
    timer.start()

    # Keep timer alive by attaching to one of the widgets
    cpu_row._sys_timer = timer
