import math
import random
import time
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (QPainter, QPen, QColor, QFont,
                          QRadialGradient, QConicalGradient, QBrush)

from giselo.app.theme import BG

_STATE_COLORS = {
    "idle":      "#3a9ee0",
    "listening": "#88c93a",
    "speaking":  "#58d8e8",
    "thinking":  "#e8c33a",
    "error":     "#e05050",
    "success":   "#88c93a",
}

# Ring config: (tilt_deg, azim_base_deg, speed, radius_factor, arc_frac, alpha_base, line_width_max)
#   tilt_deg      — inclination from horizontal (0=flat circle on screen, 90=line)
#   azim_base_deg — initial azimuth phase offset
#   speed         — spin speed multiplier vs _phi
#   radius_factor — fraction of sphere_r
#   arc_frac      — 1.0=full ring, 0.6=60% arc (rest is gap = scanning look)
#   alpha_base    — base opacity 0–1
#   line_width_max— max line width (front) in px
_STATE_RINGS = {
    "idle": [
        ( 0,   0, 0.18, 1.00, 1.0, 0.48, 2.0),
        (50,  90, 0.26, 0.92, 1.0, 0.52, 1.8),
        (75,  45, 0.20, 0.80, 1.0, 0.42, 1.5),
        (25, 180, 0.32, 0.68, 1.0, 0.38, 1.4),
        (60, 270, 0.15, 0.55, 1.0, 0.32, 1.3),
    ],
    "listening": [
        ( 0,   0, 0.42, 1.00, 1.0, 0.55, 2.2),
        (55,  90, 0.62, 0.92, 1.0, 0.60, 2.0),
        (30,  45, 0.52, 0.80, 1.0, 0.52, 1.8),
        (78, 150, 0.38, 0.68, 1.0, 0.48, 1.5),
        (18, 225, 0.30, 1.12, 1.0, 0.35, 1.6),   # outer sentinel ring
        (65, 315, 0.48, 0.52, 1.0, 0.42, 1.4),
    ],
    "thinking": [
        (15,   0, 1.20, 1.00, 0.72, 0.58, 2.2),
        (62,  45, 0.90, 0.92, 0.60, 0.55, 2.0),
        (35,  90, 1.50, 0.80, 0.80, 0.52, 1.8),
        (80, 135, 1.00, 0.68, 0.65, 0.48, 1.5),
        (50, 180, 1.30, 0.55, 0.75, 0.44, 1.4),
        (22, 225, 0.80, 1.12, 0.55, 0.35, 1.5),   # outer arc scanner
        (70, 270, 1.10, 0.42, 0.68, 0.38, 1.3),
        (10, 315, 1.60, 0.30, 0.85, 0.30, 1.2),
    ],
    "speaking": [
        ( 0,   0, 0.52, 1.00, 1.0, 0.60, 2.4),
        (65,  90, 0.72, 0.90, 1.0, 0.65, 2.2),
        (38,  45, 0.62, 0.78, 1.0, 0.58, 2.0),
        (20, 180, 0.42, 0.65, 1.0, 0.52, 1.7),
        (55, 270, 0.58, 0.52, 1.0, 0.46, 1.5),
        ( 0,   0, 0.88, 1.18, 1.0, 0.30, 1.6),   # outer reactive
    ],
    "error": [
        ( 0,   0, 0.16, 1.00, 0.45, 0.45, 1.8),
        (85,  45, 0.12, 0.82, 0.38, 0.40, 1.5),
        (42, 200, 0.10, 0.62, 0.30, 0.30, 1.3),
    ],
    "success": [
        ( 0,   0, 0.44, 1.10, 1.0, 0.70, 2.4),
        (60,  60, 0.64, 0.94, 1.0, 0.72, 2.2),
        (30,  30, 0.54, 0.80, 1.0, 0.65, 2.0),
        (78, 120, 0.38, 0.67, 1.0, 0.62, 1.8),
        (22, 200, 0.50, 0.54, 1.0, 0.58, 1.6),
        (55, 280, 0.34, 1.18, 1.0, 0.42, 1.7),   # outer burst
        (72, 340, 0.58, 0.42, 1.0, 0.55, 1.5),
        (12, 180, 0.44, 1.28, 1.0, 0.32, 1.5),   # very outer
    ],
}

# Latitude circles (horizontal slices of sphere): (height_norm, alpha_base)
# height_norm: -1 (bottom) to +1 (top), 0 = equator
_LATITUDE_RINGS = [
    ( 0.60, 0.12),
    ( 0.00, 0.18),
    (-0.60, 0.12),
]

_STATE_PARTICLE_MAX = {
    "idle": 4, "listening": 14, "thinking": 10,
    "speaking": 24, "error": 3, "success": 32,
}

_STATE_BASE_SPEED = {
    "idle": 0.007, "listening": 0.016, "thinking": 0.030,
    "speaking": 0.020, "error": 0.005, "success": 0.024,
}

NUM_BARS      = 26
FADE_STEPS    = 14
BREATH_SPEED  = 0.012
RING_SEGMENTS = 80

# ── Icosahedron wireframe (geodesic mesh) ─────────────────────────────────────
_GR   = (1 + math.sqrt(5)) / 2          # golden ratio ≈ 1.618
_ICO_N = math.sqrt(1 + _GR ** 2)        # normalisation → unit-sphere radius
_ICO_VERTS: list[tuple] = [
    tuple(c / _ICO_N for c in v)
    for v in [
        ( 0,    1,   _GR), ( 0,   -1,   _GR), ( 0,    1,  -_GR), ( 0,   -1,  -_GR),
        ( 1,   _GR,   0),  (-1,   _GR,   0),  ( 1,  -_GR,   0),  (-1,  -_GR,   0),
        (_GR,   0,    1),  (-_GR,  0,    1),  (_GR,   0,   -1),  (-_GR,  0,   -1),
    ]
]
_ICO_EDGES: list[tuple[int, int]] = [
    (0,1),(0,4),(0,5),(0,8),(0,9),
    (1,6),(1,7),(1,8),(1,9),
    (2,3),(2,4),(2,5),(2,10),(2,11),
    (3,6),(3,7),(3,10),(3,11),
    (4,5),(4,8),(4,10),
    (5,9),(5,11),
    (6,7),(6,8),(6,10),
    (7,9),(7,11),
    (8,10),(9,11),
]


class GiseloCore(QWidget):
    """Holographic 3D gyroscopic sphere — state-reactive shape, color, and animation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("center-widget")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(300, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self._state      = "idle"
        self._prev_state = "idle"
        self._fade_prog  = 1.0
        self._fade_step  = 0

        self._accent      = QColor(_STATE_COLORS["idle"])
        self._level       = 0.0
        self._phi         = 0.0
        self._breath_phase = 0.0
        self._breath_scale = 1.0

        self._bars        = [0.08] * NUM_BARS
        self._pill_text   = "● IDLE"
        self._pill_glow   = 0.5

        # Particles: (ring_idx, t_offset_on_ring, age 1→0)
        self._particles: list[tuple[int, float, float]] = []
        self._ptimer      = 0

        # Ripple rings: (radius_frac 0→1, alpha 1→0)
        self._ripples: list[tuple[float, float]] = []
        self._rtimer      = 0

        # Scan beam angle (thinking state) in radians
        self._scan_angle  = 0.0

        # Ring harmonic oscillation phase per ring index
        self._ring_phases: list[float] = [random.uniform(0, 2 * math.pi) for _ in range(10)]

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, new_state: str) -> None:
        if new_state == self._state or new_state not in _STATE_RINGS:
            return
        self._prev_state = self._state
        self._state      = new_state
        self._fade_prog  = 0.0
        self._fade_step  = 0
        self._particles.clear()
        if new_state in ("listening", "success", "speaking"):
            self._ripples.clear()

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
        self._phi = (self._phi + _STATE_BASE_SPEED.get(self._state, 0.012)) % (2 * math.pi)

        if self._fade_prog < 1.0:
            self._fade_step += 1
            self._fade_prog = min(1.0, self._fade_step / FADE_STEPS)

        if self._state == "idle":
            self._breath_phase = (self._breath_phase + BREATH_SPEED) % (2 * math.pi)
            self._breath_scale = 1.0 + 0.022 * math.sin(self._breath_phase)
        else:
            self._breath_scale = 1.0

        # Harmonic ring oscillation
        for i in range(len(self._ring_phases)):
            self._ring_phases[i] = (self._ring_phases[i] + 0.025 + i * 0.008) % (2 * math.pi)

        # Spectrum
        if self._state == "idle":
            self._bars = [
                max(0.04, min(0.35, b + random.uniform(-0.03, 0.03)))
                for b in self._bars
            ]
        elif self._state == "speaking":
            self._bars = [
                max(0.08, min(1.0, self._level * random.uniform(0.5, 1.5)))
                for _ in self._bars
            ]
        elif self._state == "thinking":
            t = time.monotonic()
            self._bars = [
                max(0.04, 0.16 + 0.18 * math.sin(t * 2.8 + i * 0.5))
                for i in range(NUM_BARS)
            ]

        # Scan beam (thinking)
        if self._state == "thinking":
            self._scan_angle = (self._scan_angle + 0.055) % (2 * math.pi)

        # Particles
        max_p = _STATE_PARTICLE_MAX.get(self._state, 0)
        if max_p > 0:
            self._ptimer += 1
            spawn_rate = max(2, 8 - max_p // 4)
            if self._ptimer >= spawn_rate and len(self._particles) < max_p * 3:
                self._ptimer = 0
                rings = _STATE_RINGS.get(self._state, [])
                if rings:
                    ri = random.randint(0, len(rings) - 1)
                    arc = rings[ri][4]
                    t_off = random.uniform(0.0, arc * 2 * math.pi)
                    self._particles.append((ri, t_off, 1.0))
            self._particles = [
                (ri, t, a - 0.028) for ri, t, a in self._particles if a > 0.025
            ]

        # Ripples
        if self._state in ("listening", "success", "speaking"):
            self._rtimer += 1
            interval = 15 if self._state == "success" else (24 if self._state == "speaking" else 34)
            if self._rtimer >= interval:
                self._rtimer = 0
                self._ripples.append((0.0, 1.0))
            spd = 0.026 if self._state == "speaking" else 0.018
            self._ripples = [
                (r + spd, a - 0.020) for r, a in self._ripples if a > 0.018
            ]
        else:
            self._ripples.clear()

        self._pill_glow = 0.5 + 0.5 * math.sin(time.monotonic() * 4.0)
        self.update()

    # ── Color helpers ─────────────────────────────────────────────────────────

    def _state_color(self, state: str) -> QColor:
        return QColor(_STATE_COLORS.get(state, _STATE_COLORS["idle"]))

    def _current_color(self) -> QColor:
        if self._fade_prog >= 1.0:
            return self._state_color(self._state)
        c0 = self._state_color(self._prev_state)
        c1 = self._state_color(self._state)
        t = self._fade_prog
        return QColor(
            int(c0.red()   * (1 - t) + c1.red()   * t),
            int(c0.green() * (1 - t) + c1.green() * t),
            int(c0.blue()  * (1 - t) + c1.blue()  * t),
        )

    # ── Ring projection ───────────────────────────────────────────────────────

    def _ring_pts(self, tilt_deg: float, azim_base_deg: float,
                  speed: float, arc_frac: float,
                  harmonic_idx: int = 0) -> list[tuple[float, float, float]]:
        """
        Orthographic projection of a tilted 3D ring.

        Derivation:
          - Start with ring in XY plane: P(t) = (cos t, sin t, 0)
          - Tilt around X axis by `tilt`: (cos t, sin t·cos(tilt), sin t·sin(tilt))
          - Rotate around Z axis by `azim`: apply 2D rotation to XY components
          - Project to screen: screen = (r·x, r·y), depth = z
        """
        tilt  = math.radians(tilt_deg)
        azim  = math.radians(azim_base_deg) + self._phi * speed
        ct    = math.cos(tilt)
        st    = math.sin(tilt)
        ca    = math.cos(azim)
        sa    = math.sin(azim)

        # Subtle harmonic radius pulsation
        h_scale = 1.0 + 0.030 * math.sin(self._ring_phases[harmonic_idx % len(self._ring_phases)])

        steps     = RING_SEGMENTS
        arc_steps = max(4, int(steps * arc_frac))
        pts: list[tuple[float, float, float]] = []
        for si in range(arc_steps + 1):
            t  = si * 2 * math.pi / steps
            lx = math.cos(t) * h_scale
            ly = math.sin(t) * ct * h_scale
            x  = lx * ca - ly * sa
            y  = lx * sa + ly * ca
            z  = math.sin(t) * st
            pts.append((x, y, z))
        return pts

    def _ring_pt_at(self, t: float, tilt_deg: float,
                    azim_base_deg: float, speed: float) -> tuple[float, float, float]:
        tilt = math.radians(tilt_deg)
        azim = math.radians(azim_base_deg) + self._phi * speed
        ct, st = math.cos(tilt), math.sin(tilt)
        ca, sa = math.cos(azim), math.sin(azim)
        lx = math.cos(t)
        ly = math.sin(t) * ct
        x  = lx * ca - ly * sa
        y  = lx * sa + ly * ca
        z  = math.sin(t) * st
        return x, y, z

    # ── Icosahedron geodesic mesh ─────────────────────────────────────────────

    def _ico_xform(self, v: tuple, tumble: float) -> tuple[float, float, float]:
        """Rotate vert: slow Y-axis tumble + fixed 22° X tilt."""
        x, y, z = v
        ca, sa = math.cos(tumble), math.sin(tumble)
        x2, z2 = x * ca + z * sa, -x * sa + z * ca
        tilt = 0.384   # ≈ 22° in radians
        ct, st = math.cos(tilt), math.sin(tilt)
        y3 = y * ct - z2 * st
        z3 = y * st + z2 * ct
        return x2, y3, z3

    def _draw_geodesic_mesh(self, p, cx: float, cy: float, sphere_r: float) -> None:
        color  = self._current_color()
        tumble = self._phi * 0.28          # much slower than orbital rings
        proj   = [self._ico_xform(v, tumble) for v in _ICO_VERTS]

        # ── edges ──────────────────────────────────────────────────────────
        for i, j in _ICO_EDGES:
            x1, y1, z1 = proj[i]
            x2, y2, z2 = proj[j]
            depth   = (z1 + z2) / 2.0
            depth_a = 0.08 + 0.40 * (depth + 1.0) / 2.0
            alpha   = int(depth_a * 230 * self._fade_prog)
            c = QColor(color); c.setAlpha(max(0, min(255, alpha)))
            lw = 0.3 + 1.0 * (depth + 1.0) / 2.0
            pen = QPen(c, lw)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(
                QPointF(cx + sphere_r * x1, cy + sphere_r * y1),
                QPointF(cx + sphere_r * x2, cy + sphere_r * y2),
            )

        # ── vertex nodes ───────────────────────────────────────────────────
        p.setPen(Qt.PenStyle.NoPen)
        for x, y, z in proj:
            depth_a = 0.22 + 0.78 * (z + 1.0) / 2.0
            node_r  = 0.8 + 2.0 * (z + 1.0) / 2.0
            c = QColor(color); c.setAlpha(int(depth_a * 245 * self._fade_prog))
            p.setBrush(QBrush(c))
            p.drawEllipse(QPointF(cx + sphere_r * x, cy + sphere_r * y), node_r, node_r)
            # Hot-white core on front-facing nodes
            if z > 0.2:
                cw = QColor(255, 255, 255, int(((z - 0.2) / 0.8) * 200 * self._fade_prog))
                p.setBrush(QBrush(cw))
                p.drawEllipse(QPointF(cx + sphere_r * x, cy + sphere_r * y),
                              node_r * 0.36, node_r * 0.36)

    # ── Iron Man corner HUD brackets ─────────────────────────────────────────

    def _draw_hud_brackets(self, p, cx: float, cy: float, ring_size: float) -> None:
        color = self._current_color()
        glow  = 0.22 + 0.10 * self._pill_glow
        c = QColor(color); c.setAlphaF(glow)
        pen = QPen(c, 1.2)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        br = ring_size * 0.495   # half-span of bracket frame
        bl = ring_size * 0.092   # arm length

        corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
        for dx, dy in corners:
            bx, by = cx + dx * br, cy + dy * br
            p.drawLine(QPointF(bx, by), QPointF(bx - dx * bl, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by - dy * bl))

        # Small arc inside each bracket corner
        c2 = QColor(color); c2.setAlphaF(glow * 0.60)
        p.setPen(QPen(c2, 0.8))
        arc_r = bl * 0.55
        arc_starts = {(-1,-1): 180, (1,-1): 270, (1,1): 0, (-1,1): 90}
        for dx, dy in corners:
            bx, by = cx + dx * br, cy + dy * br
            start = arc_starts[(dx, dy)]
            p.drawArc(
                QRectF(bx - arc_r + dx * arc_r * 0.4,
                       by - arc_r + dy * arc_r * 0.4,
                       arc_r * 2, arc_r * 2),
                start * 16, 90 * 16,
            )

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(BG))

        W, H = self.width(), self.height()
        cx, cy = W / 2.0, H / 2.0
        ring_size = min(W * 0.78, H * 0.55, 460.0)
        sphere_r  = ring_size * 0.40 * self._breath_scale
        if self._state == "speaking":
            sphere_r *= 1.0 + self._level * 0.12

        self._draw_glow(p, cx, cy, sphere_r)
        self._draw_outer_hud(p, cx, cy, ring_size)
        self._draw_hud_brackets(p, cx, cy, ring_size)
        self._draw_ripples(p, cx, cy, sphere_r)
        self._draw_latitude_rings(p, cx, cy, sphere_r)
        self._draw_geodesic_mesh(p, cx, cy, sphere_r)
        self._draw_sphere_rings(p, cx, cy, sphere_r)
        self._draw_scan_beam(p, cx, cy, sphere_r)
        self._draw_particles(p, cx, cy, sphere_r)
        self._draw_core(p, cx, cy, sphere_r * 0.18)
        self._draw_spectrum(p, cx, cy, ring_size)
        self._draw_pill(p, cx, cy, ring_size)
        p.end()

    # ── Glow ─────────────────────────────────────────────────────────────────

    def _draw_glow(self, p, cx, cy, sphere_r):
        color = self._current_color()
        r = sphere_r * 2.4 + self._level * sphere_r * 0.8
        grad = QRadialGradient(QPointF(cx, cy), r)
        c0 = QColor(color); c0.setAlphaF(0.26 + self._level * 0.16)
        c1 = QColor(color); c1.setAlphaF(0.0)
        grad.setColorAt(0.0, c0)
        grad.setColorAt(0.55, QColor(c0.red(), c0.green(), c0.blue(), int(c0.alpha() * 0.3)))
        grad.setColorAt(1.0, c1)
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r, r)

    # ── Outer flat HUD rings ──────────────────────────────────────────────────

    def _draw_outer_hud(self, p, cx, cy, ring_size):
        color = self._current_color()
        opacities = [0.30, 0.20, 0.14, 0.09, 0.06]
        pulse = 1.0 + (self._level * 0.06 if self._state == "speaking" else 0.0)
        n = 5
        hud_deg = math.degrees(self._phi)

        for i in range(n):
            r = ring_size * 0.5 * ((i + 1) / n) * pulse
            c = QColor(color); c.setAlpha(int(opacities[i] * 255))
            pen = QPen(c, 1.1)
            if i % 2 == 1:
                pen.setDashPattern([6.0, 5.0])
                pen.setDashOffset(hud_deg * (i + 1) * 0.13)
            p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r, r)

        # Tick marks
        outer_r  = ring_size * 0.5 * pulse
        tick_end = outer_r + 6.0
        tc = QColor(color); tc.setAlpha(42)
        p.setPen(QPen(tc, 0.8))
        phi_r = self._phi * 0.09
        for k in range(24):
            ang = math.radians(k * 15) + phi_r
            p.drawLine(
                QPointF(cx + outer_r * math.cos(ang), cy + outer_r * math.sin(ang)),
                QPointF(cx + tick_end * math.cos(ang), cy + tick_end * math.sin(ang)),
            )

    # ── Ripple rings ─────────────────────────────────────────────────────────

    def _draw_ripples(self, p, cx, cy, sphere_r):
        color = self._current_color()
        for rad_frac, alpha in self._ripples:
            rr = sphere_r * (1.05 + rad_frac * 1.4)
            c = QColor(color); c.setAlpha(int(alpha * 160))
            p.setPen(QPen(c, 1.3)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), rr, rr)

    # ── Latitude circles (horizontal slices of the sphere) ───────────────────

    def _draw_latitude_rings(self, p, cx, cy, sphere_r):
        color = self._current_color()
        for h, base_alpha in _LATITUDE_RINGS:
            slice_r = sphere_r * math.sqrt(max(0.0, 1.0 - h * h))
            if slice_r < 4:
                continue
            y_off = cy + sphere_r * h * 0.28   # subtle vertical offset for 3D feel
            alpha = int(base_alpha * 180 * self._fade_prog)
            c = QColor(color); c.setAlpha(alpha)
            pen = QPen(c, 0.8)
            pen.setDashPattern([4.0, 6.0])
            pen.setDashOffset(math.degrees(self._phi) * 0.12 * (1 + h))
            p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, y_off), slice_r, slice_r * 0.30)

    # ── 3D holographic sphere orbital rings ───────────────────────────────────

    def _draw_sphere_rings(self, p, cx, cy, sphere_r):
        color      = self._current_color()
        prev_color = self._state_color(self._prev_state)
        rings_cur  = _STATE_RINGS.get(self._state,      _STATE_RINGS["idle"])
        rings_prev = _STATE_RINGS.get(self._prev_state, _STATE_RINGS["idle"])
        level_boost = 1.0 + self._level * 0.12

        def _draw_one(ring_cfg, color_q, alpha_mult, ring_i):
            tilt, azim, speed, r_fac, arc, alpha_b, lw_max = ring_cfg
            r   = sphere_r * r_fac * level_boost
            pts = self._ring_pts(tilt, azim, speed, arc, ring_i)
            for si in range(len(pts) - 1):
                x1, y1, z1 = pts[si]
                x2, y2, z2 = pts[si + 1]
                depth   = (z1 + z2) / 2.0
                depth_a = 0.18 + 0.82 * (depth + 1.0) / 2.0
                alpha   = int(alpha_b * depth_a * alpha_mult * 255)
                c = QColor(color_q); c.setAlpha(max(0, min(255, alpha)))
                w = 0.5 + lw_max * (depth + 1.0) / 2.0
                pen = QPen(c, w)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                p.drawLine(
                    QPointF(cx + r * x1, cy + r * y1),
                    QPointF(cx + r * x2, cy + r * y2),
                )

        for ri, ring_cfg in enumerate(rings_cur):
            extra = self._fade_prog if ri >= len(rings_prev) else 1.0
            _draw_one(ring_cfg, color, extra, ri)

        if self._fade_prog < 1.0:
            for ri, ring_cfg in enumerate(rings_prev):
                if ri >= len(rings_cur):
                    _draw_one(ring_cfg, prev_color, 1.0 - self._fade_prog, ri)

    # ── Scan beam (thinking state) ────────────────────────────────────────────

    def _draw_scan_beam(self, p, cx, cy, sphere_r):
        if self._state != "thinking":
            return
        color = self._current_color()
        # Draw a bright rotating wedge/sector as if scanning the sphere
        # Represented as a fading arc on the outer ring + a bright line
        angle = self._scan_angle
        for i in range(18):
            trail_angle = angle - i * 0.06
            alpha = int(200 * (1.0 - i / 18.0) * self._fade_prog)
            if alpha < 5:
                break
            c = QColor(color); c.setAlpha(alpha)
            rr = sphere_r * 1.02
            x = cx + rr * math.cos(trail_angle)
            y = cy + rr * math.sin(trail_angle)
            dot_r = 2.0 * (1.0 - i / 18.0)
            p.setBrush(QBrush(c)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, y), dot_r, dot_r)

        # Sweep line from center to edge
        c2 = QColor(color); c2.setAlpha(int(80 * self._fade_prog))
        p.setPen(QPen(c2, 0.8))
        p.drawLine(
            QPointF(cx, cy),
            QPointF(cx + sphere_r * 1.08 * math.cos(angle),
                    cy + sphere_r * 1.08 * math.sin(angle)),
        )

    # ── Energy particles along rings ──────────────────────────────────────────

    def _draw_particles(self, p, cx, cy, sphere_r):
        if not self._particles:
            return
        rings_cfg   = _STATE_RINGS.get(self._state, [])
        level_boost = 1.0 + self._level * 0.12
        color       = self._current_color()

        for ri, t_off, age in self._particles:
            if ri >= len(rings_cfg):
                continue
            tilt, azim, speed, r_fac, _, _, _ = rings_cfg[ri]
            x, y, z = self._ring_pt_at(t_off, tilt, azim, speed)
            r   = sphere_r * r_fac * level_boost
            sx, sy = cx + r * x, cy + r * y
            depth_a = 0.28 + 0.72 * (z + 1.0) / 2.0
            alpha   = int(age * depth_a * 255)
            c = QColor(color); c.setAlpha(max(0, min(255, alpha)))

            # Main dot
            dot_r = 1.0 + 2.5 * age
            p.setBrush(QBrush(c)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(sx, sy), dot_r, dot_r)

            # White hot core for bigger particles
            if age > 0.65:
                cw = QColor(255, 255, 255, int(age * 160))
                p.setBrush(QBrush(cw))
                p.drawEllipse(QPointF(sx, sy), dot_r * 0.35, dot_r * 0.35)

    # ── Glowing core ─────────────────────────────────────────────────────────

    def _draw_core(self, p, cx, cy, core_r):
        color = self._current_color()
        pulse = 0.65 + 0.35 * math.sin(self._breath_phase * 3.2 + time.monotonic() * 2.5)
        r = core_r * (1.0 + self._level * 0.7) * pulse

        # Outer colored halo
        grad = QRadialGradient(QPointF(cx, cy), r * 2.8)
        ch = QColor(color); ch.setAlphaF(0.22 * pulse)
        ch0 = QColor(color); ch0.setAlphaF(0.0)
        grad.setColorAt(0.0, ch); grad.setColorAt(1.0, ch0)
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r * 2.8, r * 2.8)

        # Inner glow
        grad2 = QRadialGradient(QPointF(cx, cy), r)
        c_white = QColor(255, 255, 255, int(240 * pulse))
        c_mid   = QColor(color); c_mid.setAlphaF(0.90)
        c_edge  = QColor(color); c_edge.setAlphaF(0.0)
        grad2.setColorAt(0.00, c_white)
        grad2.setColorAt(0.40, c_mid)
        grad2.setColorAt(1.00, c_edge)
        p.setBrush(QBrush(grad2))
        p.drawEllipse(QPointF(cx, cy), r, r)

    # ── Spectrum bars ─────────────────────────────────────────────────────────

    def _draw_spectrum(self, p, cx, cy, ring_size):
        color  = self._current_color()
        area_w = ring_size * 0.70
        max_h, min_h = 38.0, 3.0
        bar_w  = area_w / (NUM_BARS * 1.55)
        gap    = bar_w * 0.55
        total  = NUM_BARS * (bar_w + gap) - gap
        x0     = cx - total / 2.0
        y_base = cy + ring_size * 0.53

        for i, lvl in enumerate(self._bars):
            bar_h = min_h + lvl * (max_h - min_h)
            x = x0 + i * (bar_w + gap)
            cd = abs(i - NUM_BARS / 2) / (NUM_BARS / 2)
            c = QColor(color); c.setAlphaF(0.72 - cd * 0.28)
            p.setBrush(QBrush(c)); p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, y_base - bar_h, bar_w, bar_h), 1.5, 1.5)

    # ── Status pill ───────────────────────────────────────────────────────────

    def _draw_pill(self, p, cx, cy, ring_size):
        color = self._current_color()
        font  = QFont("JetBrains Mono"); font.setPointSize(8)
        p.setFont(font)
        fm     = p.fontMetrics()
        tw     = fm.horizontalAdvance(self._pill_text)
        th     = fm.height()
        pad    = 10
        pill_w = tw + pad * 2
        pill_h = th + 8
        px_    = cx - pill_w / 2
        py_    = cy - ring_size * 0.53 - pill_h - 2

        glow_r = max(pill_w, pill_h) * 0.85
        gc  = QColor(color); gc.setAlphaF(0.14 * self._pill_glow)
        gc2 = QColor(color); gc2.setAlphaF(0.0)
        grad = QRadialGradient(QPointF(cx, py_ + pill_h / 2), glow_r)
        grad.setColorAt(0, gc); grad.setColorAt(1, gc2)
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, py_ + pill_h / 2), glow_r, glow_r * 0.6)

        bg = QColor(BG); bg.setAlpha(235)
        p.setBrush(QBrush(bg))
        border = QColor(color); border.setAlphaF(0.65 + 0.35 * self._pill_glow)
        p.setPen(QPen(border, 1.0))
        p.drawRoundedRect(QRectF(px_, py_, pill_w, pill_h), 3, 3)

        p.setPen(QPen(color))
        p.drawText(QPointF(px_ + pad, py_ + th + 2), self._pill_text)
