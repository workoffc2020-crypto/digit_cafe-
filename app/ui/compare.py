"""Original-vs-enhanced comparison widget: divider slider, wheel zoom, Fit/100%/200%, drag to pan."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget


class CompareView(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.left = None
        self.right = None
        self.split = 0.5
        self.zoom = 0.0          # 0 => fit
        self.offset = QPointF(0, 0)
        self._drag = None
        self._drag_split = False
        self.setMouseTracking(True)

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(640, 480)

    def set_images(self, left: QPixmap, right: QPixmap = None, keep_view: bool = False):
        same = (keep_view and self.left is not None and left is not None
                and self.left.size() == left.size())
        self.left, self.right = left, right
        if not same:
            self.zoom, self.offset = 0.0, QPointF(0, 0)
        self.update()

    def set_zoom_percent(self, pct: float):
        if self._ref():
            self.zoom = pct / 100.0
            self.offset = QPointF(0, 0)
            self.update()

    def fit(self):
        self.zoom, self.offset = 0.0, QPointF(0, 0)
        self.update()

    def _ref(self):
        return self.right or self.left

    def _rect(self):
        ref = self._ref()
        if not ref:
            return QRectF()
        w, h = ref.width(), ref.height()
        fit = min(self.width() / w, self.height() / h)
        z = fit if self.zoom <= 0 else self.zoom
        rw, rh = w * z, h * z
        return QRectF((self.width() - rw) / 2 + self.offset.x(), (self.height() - rh) / 2 + self.offset.y(), rw, rh)

    def _pill(self, p, x, y, text, color):
        f = QFont(p.font())
        f.setBold(True)
        f.setPointSize(8)
        p.setFont(f)
        w = p.fontMetrics().horizontalAdvance(text) + 18
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(x, y, w, 22), 11, 11)
        p.setPen(QColor("white"))
        p.drawText(QRectF(x, y, w, 22), Qt.AlignCenter, text)
        return w

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform, self.zoom <= 0 or self.zoom < 1)
        p.fillRect(self.rect(), QColor("#0a0e18"))
        if not self.left:
            p.setPen(QPen(QColor("#2a3550"), 2, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(14, 14, -14, -14), 16, 16)
            p.setPen(QColor("#8d97b2"))
            f = QFont(p.font())
            f.setPointSize(11)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter, "🖼  Preview area\n\nAdd an image to see it here")
            return
        r = self._rect()
        if self.right is None:
            p.drawPixmap(r, self.left, QRectF(self.left.rect()))
            return
        sx = r.left() + r.width() * self.split
        p.save()
        p.setClipRect(QRectF(0, 0, sx, self.height()))
        p.drawPixmap(r, self.left, QRectF(self.left.rect()))
        p.restore()
        p.save()
        p.setClipRect(QRectF(sx, 0, self.width() - sx, self.height()))
        p.drawPixmap(r, self.right, QRectF(self.right.rect()))
        p.restore()
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawLine(int(sx), 0, int(sx), self.height())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#14b8a6"))
        p.drawEllipse(QPointF(sx, self.height() / 2), 16, 16)
        p.setPen(QColor("white"))
        p.drawText(QRectF(sx - 16, self.height() / 2 - 16, 32, 32), Qt.AlignCenter, "⇆")
        self._pill(p, 10, 10, "ORIGINAL", "#334155")
        w = self._pill(p, 0, -100, "ENHANCED", "#6366f1")
        self._pill(p, self.width() - w - 10, 10, "ENHANCED", "#6366f1")

    def mousePressEvent(self, e):
        if self.right is not None:
            r = self._rect()
            if abs(e.position().x() - (r.left() + r.width() * self.split)) < 20:
                self._drag_split = True
                return
        self._drag = e.position()

    def mouseMoveEvent(self, e):
        if self._drag_split:
            r = self._rect()
            if r.width() > 0:
                self.split = min(max((e.position().x() - r.left()) / r.width(), 0.0), 1.0)
                self.update()
        elif self._drag is not None:
            self.offset += e.position() - self._drag
            self._drag = e.position()
            self.update()

    def mouseReleaseEvent(self, _):
        self._drag = None
        self._drag_split = False

    def wheelEvent(self, e):
        ref = self._ref()
        if not ref:
            return
        fit = min(self.width() / ref.width(), self.height() / ref.height())
        z = fit if self.zoom <= 0 else self.zoom
        z *= 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.zoom = min(max(z, fit * 0.5), 16.0)
        self.update()
