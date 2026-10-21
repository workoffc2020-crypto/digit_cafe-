from __future__ import annotations

import os
import sys
from dataclasses import replace

from PIL import Image, ImageOps
from PySide6.QtCore import QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QGuiApplication, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFrame,
                               QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea,
                               QSizePolicy, QSlider, QSpinBox, QSplitter, QStackedWidget, QTabWidget, QTextEdit,
                               QVBoxLayout, QWidget)

from app import APP_NAME, APP_VERSION
from app.core import enhance as E
from app.core import jobs, recent
from app.core.logging_setup import log_dir
from app.core.pdf_engine import PAGE_SIZES_MM, PdfOptions
from app.core.sysinfo import available_ram_bytes, estimate_enhance_bytes, gpu_providers
from app.ui.compare import CompareView
from app.ui.pdf_tools import PdfToolsPage
from app.ui.worker import Worker

IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".gif")
LIVE_MAX_SIDE = 1600

STYLE = """
* { font-family:'Segoe UI','Inter',Arial; font-size:13px; }
QMainWindow, QWidget { background:#0b0f1a; color:#e8ecf6; }
QLabel, QCheckBox, QSlider, QSplitter { background:transparent; }
QToolTip { background:#1b2440; color:#e8ecf6; border:1px solid #3b4a75; padding:4px; }

/* ---------- sidebar ---------- */
#sidebar { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0f1628,stop:1 #0a0e1a); border-right:1px solid #1c2440; }
#sidebar QPushButton { text-align:left; padding:12px 16px; border:none; border-radius:10px; color:#9aa6c4;
                       font-size:14px; background:transparent; }
#sidebar QPushButton:hover { background:#18213a; color:white; }
#sidebar QPushButton:checked { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0ea5a0,stop:1 #6366f1); color:white; font-weight:600; }

/* ---------- panels ---------- */
#panel { background:#0f1524; border:1px solid #1f2944; border-radius:14px; }
#panelTitle { color:#7dd3cf; font-weight:600; font-size:13px; }
#banner { border-radius:18px;
          background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0ea5a0,stop:0.55 #6366f1,stop:1 #a855f7); }
#bannerTitle { font-size:26px; font-weight:700; color:white; background:transparent; }
#bannerSub { color:rgba(255,255,255,0.88); font-size:14px; background:transparent; }
#chip { background:rgba(255,255,255,0.20); color:white; border-radius:11px; padding:4px 12px; font-weight:600; }
#card { background:#121a2e; border:1px solid #1f2944; border-radius:16px; }
#cardTitle { font-size:16px; font-weight:700; color:white; }
#cardDesc { color:#98a3c0; }

/* ---------- buttons ---------- */
QPushButton { background:#19223a; border:1px solid #2a3558; border-radius:9px; padding:8px 14px; color:#dfe5f5; }
QPushButton:hover { background:#222d4d; border-color:#3d4d7c; }
QPushButton:pressed { background:#141b30; }
QPushButton:disabled { color:#5d6788; background:#131a2c; border-color:#1f2944; }

#btnLossless { border:none; border-radius:14px; font-size:15px; font-weight:700; color:white; padding:15px 18px;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #10b981,stop:1 #06b6d4); }
#btnLossless:hover { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #34d399,stop:1 #22d3ee); }
#btnLossless:pressed { background:#0e9f74; }
#btnLossless:disabled { background:#16342f; color:#6b8b84; }

#btnAI { border:none; border-radius:14px; font-size:15px; font-weight:700; color:white; padding:15px 18px;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #6366f1,stop:0.55 #a855f7,stop:1 #ec4899); }
#btnAI:hover { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7c7ff7,stop:0.55 #bd7bfa,stop:1 #f472b6); }
#btnAI:pressed { background:#7c3aed; }
#btnAI:disabled { background:#2a2547; color:#7d77a3; }

#btnPreview { background:transparent; border:2px solid #22d3ee; color:#67e8f9; font-weight:600; border-radius:12px; padding:10px 14px; }
#btnPreview:hover { background:rgba(34,211,238,0.14); }
#btnPreview:disabled { border-color:#1f4a52; color:#3f6c75; }

#btnSave { border:none; border-radius:12px; font-weight:700; color:#1b1300; padding:10px 14px;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #fbbf24,stop:1 #f59e0b); }
#btnSave:hover { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #fcd34d,stop:1 #fbbf24); }
#btnSave:disabled { background:#3b3318; color:#8a7a45; }

#btnDanger { background:transparent; border:1px solid #ef4444; color:#fca5a5; font-weight:600; }
#btnDanger:hover { background:rgba(239,68,68,0.18); }
#btnDanger:disabled { border-color:#4a2a2f; color:#6b4a4f; }

#btnAdd { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0ea5a0,stop:1 #14b8a6); border:none; color:white; font-weight:600; }
#btnAdd:hover { background:#22c7bf; }
#btnReset { background:transparent; border:1px solid #3d4d7c; color:#b7c3e6; }

/* ---------- inputs ---------- */
QComboBox, QSpinBox, QDoubleSpinBox { background:#141c33; border:1px solid #2a3558; border-radius:8px; padding:5px 8px; min-height:20px; }
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color:#14b8a6; }
QComboBox QAbstractItemView { background:#141c33; border:1px solid #2a3558; selection-background-color:#0ea5a0; }
QCheckBox { spacing:8px; }
QCheckBox::indicator { width:18px; height:18px; border-radius:5px; border:1px solid #3b4a75; background:#0f1528; }
QCheckBox::indicator:hover { border-color:#14b8a6; }
QCheckBox::indicator:checked { border:1px solid #14b8a6;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #14b8a6,stop:1 #6366f1); }

QSlider::groove:horizontal { height:6px; background:#222c4a; border-radius:3px; }
QSlider::sub-page:horizontal { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #14b8a6,stop:1 #6366f1); border-radius:3px; }
QSlider::handle:horizontal { background:white; width:16px; height:16px; margin:-6px 0; border-radius:9px; border:2px solid #14b8a6; }
QSlider::handle:horizontal:hover { border-color:#a855f7; background:#f1f5ff; }
#valueChip { background:#17213d; color:#7dd3cf; border-radius:8px; padding:1px 9px; font-weight:600; min-width:42px; }

QTabWidget::pane { border:none; }
QTabBar::tab { background:#131b31; color:#9aa6c4; padding:9px 14px; border-top-left-radius:10px; border-top-right-radius:10px; margin-right:3px; }
QTabBar::tab:selected { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0ea5a0,stop:1 #6366f1); color:white; font-weight:600; }
QTabBar::tab:hover:!selected { background:#1b2542; color:white; }

QListWidget { background:#0b1020; border:1px solid #1f2944; border-radius:12px; }
QListWidget::item { border-radius:10px; padding:4px; color:#c8d1ea; }
QListWidget::item:selected { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0e7e7a,stop:1 #4547b5); color:white; }
QListWidget::item:hover:!selected { background:#161f38; }

QProgressBar { border:none; border-radius:8px; text-align:center; background:#141c33; min-height:18px; color:white; }
QProgressBar::chunk { border-radius:8px; background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #14b8a6,stop:1 #a855f7); }
QTextEdit { background:#0b1020; border:1px solid #1f2944; font-family:Consolas,monospace; border-radius:10px; }
#badge { background:#10312f; color:#7ef0e2; border-radius:12px; padding:6px 14px; font-weight:600; }
#warn { color:#fbbf24; }
#hint { color:#7d88a8; }

QSplitter::handle { background:transparent; }
QSplitter::handle:hover { background:#14b8a6; border-radius:2px; }
QScrollArea { border:none; background:transparent; }
QScrollBar:vertical { background:transparent; width:10px; margin:2px; }
QScrollBar::handle:vertical { background:#2a3558; border-radius:4px; min-height:30px; }
QScrollBar::handle:vertical:hover { background:#14b8a6; }
QScrollBar:horizontal { background:transparent; height:10px; margin:2px; }
QScrollBar::handle:horizontal { background:#2a3558; border-radius:4px; min-width:30px; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
"""


def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(base, rel)


def pil_to_pixmap(im: Image.Image) -> QPixmap:
    im = im.convert("RGB")
    data = im.tobytes("raw", "RGB")
    qi = QImage(data, im.width, im.height, im.width * 3, QImage.Format_RGB888).copy()
    return QPixmap.fromImage(qi)


def scroll(widget: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.NoFrame)
    sa.setWidget(widget)
    return sa


def glow(widget: QWidget, color: str, blur=30, dy=5, alpha=150):
    eff = QGraphicsDropShadowEffect(widget)
    c = QColor(color)
    c.setAlpha(alpha)
    eff.setColor(c)
    eff.setBlurRadius(blur)
    eff.setOffset(0, dy)
    widget.setGraphicsEffect(eff)


def rgba(hex_color: str, a: float) -> str:
    c = QColor(hex_color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{a})"


class SliderRow(QWidget):
    """Label + slider + live value chip."""
    def __init__(self, label: str, lo: int, hi: int, signed: bool = False, tip: str = ""):
        super().__init__()
        self.signed = signed
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 3, 0, 3)
        v.setSpacing(3)
        top = QHBoxLayout()
        self.name = QLabel(label)
        self.val = QLabel("0")
        self.val.setObjectName("valueChip")
        self.val.setAlignment(Qt.AlignCenter)
        top.addWidget(self.name)
        top.addStretch()
        top.addWidget(self.val)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(lo, hi)
        self.slider.setValue(0)
        if tip:
            self.setToolTip(tip)
        self.slider.valueChanged.connect(self._upd)
        v.addLayout(top)
        v.addWidget(self.slider)
        self._upd(0)

    def _upd(self, x):
        self.val.setText(f"{x:+d}" if self.signed else f"{x}%")


class ClickableFrame(QFrame):
    clicked = Signal()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class FileList(QListWidget):
    def __init__(self, on_files):
        super().__init__()
        self._on_files = on_files
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(92, 92))
        self.setGridSize(QSize(116, 136))
        self.setResizeMode(QListWidget.Adjust)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setWordWrap(True)
        self.setMovement(QListWidget.Snap)
        self.setMinimumHeight(140)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.count() == 0:
            p = QPainter(self.viewport())
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor("#2d3a5e"), 2, Qt.DashLine))
            r = self.viewport().rect().adjusted(12, 12, -12, -12)
            p.drawRoundedRect(r, 14, 14)
            p.setPen(QColor("#8d97b2"))
            p.drawText(r, Qt.AlignCenter, "⬇\n\nDrag && drop images here\nor use  ➕ Add files")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self._on_files([u.toLocalFile() for u in e.mimeData().urls()])
            e.acceptProposedAction()
        else:
            super().dropEvent(e)


class DashboardPage(QWidget):
    """Banner + card grid that re-flows to 3 / 2 / 1 columns as the window changes size."""
    def __init__(self, banner: QWidget, cards: list):
        super().__init__()
        self.cards, self.cols = cards, 0
        v = QVBoxLayout(self)
        v.setContentsMargins(26, 22, 26, 22)
        v.setSpacing(18)
        v.addWidget(banner)
        self.grid = QGridLayout()
        self.grid.setSpacing(16)
        v.addLayout(self.grid)
        v.addStretch()
        self._flow(3)

    def _flow(self, cols):
        if cols == self.cols:
            return
        self.cols = cols
        for c in self.cards:
            self.grid.removeWidget(c)
        for i, c in enumerate(self.cards):
            self.grid.addWidget(c, i // cols, i % cols)
        for k in range(3):
            self.grid.setColumnStretch(k, 1 if k < cols else 0)

    def resizeEvent(self, e):
        w = e.size().width()
        self._flow(3 if w > 980 else 2 if w > 620 else 1)
        super().resizeEvent(e)


class ReportDialog(QDialog):
    def __init__(self, parent, text, pdf_path=None):
        super().__init__(parent)
        self.setWindowTitle("Quality Verification Report")
        self.resize(780, 580)
        lay = QVBoxLayout(self)
        t = QTextEdit()
        t.setReadOnly(True)
        t.setPlainText(text)
        lay.addWidget(t)
        row = QHBoxLayout()
        save = QPushButton("💾  Save report…")
        save.clicked.connect(lambda: self._save(text))
        row.addWidget(save)
        if pdf_path:
            op = QPushButton("📄  Open PDF")
            op.setObjectName("btnAdd")
            op.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path)))
            row.addWidget(op)
            fo = QPushButton("📂  Show in folder")
            fo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(pdf_path))))
            row.addWidget(fo)
        row.addStretch()
        c = QPushButton("Close")
        c.clicked.connect(self.accept)
        row.addWidget(c)
        lay.addLayout(row)

    def _save(self, text):
        p, _ = QFileDialog.getSaveFileName(self, "Save report", "quality_report.txt", "Text (*.txt)")
        if p:
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setWindowIcon(QIcon(resource_path("assets/app.ico")))
        self.setStyleSheet(STYLE)
        self.setMinimumSize(720, 500)           # small minimum: the window can be freely resized / snapped
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(1360, int(scr.width() * 0.92)), min(860, int(scr.height() * 0.90)))
        self.move(scr.center().x() - self.width() // 2, scr.center().y() - self.height() // 2)

        self.worker = None
        self.preview_result = None
        self._preview_key = None
        self.files: list[str] = []
        self._compact = None
        self._live_workers = set()
        self._live_pending = False
        self._live_running = False
        self._proxy = None            # (path, PIL proxy, QPixmap)
        self._live_timer = QTimer(self)
        self._live_timer.setSingleShot(True)
        self._live_timer.setInterval(300)
        self._live_timer.timeout.connect(self._live_fire)

        root = QWidget()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self._build_sidebar())
        self.stack = QStackedWidget()
        h.addWidget(self.stack, 1)
        self.stack.addWidget(scroll(self._build_dashboard()))
        self.stack.addWidget(self._build_workspace())   # not scrolled: action bar stays pinned at the bottom
        self.pdf_tools = PdfToolsPage()
        self.stack.addWidget(self.pdf_tools)             # index 2: PDF -> Image / Word / Excel (action bar pinned too)
        self.stack.addWidget(scroll(self._build_recent()))   # index 3
        self._goto(0)
        self._apply_preset(list(E.PRESETS)[0])
        self._set_compact(self.width() < 1000)
        self._reflow_actions()

    # ------------------------------------------------------------ sidebar
    def _build_sidebar(self):
        sb = QFrame()
        sb.setObjectName("sidebar")
        self.sidebar = sb
        sb.setFixedWidth(220)
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(12, 16, 12, 14)
        lay.setSpacing(6)
        self.logo = QLabel()
        self.logo.setPixmap(QPixmap(resource_path("assets/app.png")).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo.setAlignment(Qt.AlignCenter)
        self.brand = QLabel(f"<b style='font-size:16px;color:white'>{APP_NAME}</b><br>"
                            "<span style='color:#7d88a8'>Offline • Private • Fast</span>")
        self.brand.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.logo)
        lay.addWidget(self.brand)
        lay.addSpacing(12)
        self.nav, self.nav_defs = [], [("🏠", "Dashboard", 0), ("🛠️", "Image → PDF", 1), ("📑", "PDF Tools", 2), ("🕘", "Recent Projects", 3)]
        for icon, txt, idx in self.nav_defs:
            b = QPushButton(f"{icon}  {txt}")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, i=idx: self._goto(i))
            lay.addWidget(b)
            self.nav.append(b)
        lay.addStretch()
        self.about_btn = QPushButton("ℹ️  About / Hardware")
        self.about_btn.clicked.connect(self._about)
        lay.addWidget(self.about_btn)
        return sb

    def _set_compact(self, on: bool):
        if on == self._compact:
            return
        self._compact = on
        self.sidebar.setFixedWidth(68 if on else 220)
        self.brand.setVisible(not on)
        self.logo.setPixmap(QPixmap(resource_path("assets/app.png")).scaled(
            40 if on else 60, 40 if on else 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        for b, (icon, txt, _) in zip(self.nav, self.nav_defs):
            b.setText(icon if on else f"{icon}  {txt}")
            b.setToolTip(txt if on else "")
            if on:
                b.setStyleSheet("text-align:center; padding:12px 0;")
            else:
                b.setStyleSheet("")
        self.about_btn.setText("ℹ️" if on else "ℹ️  About / Hardware")

    def _reflow_actions(self):
        g = getattr(self, "_act_grid", None)
        if g is None:
            return
        wide = self.width() >= 1180
        if wide == getattr(self, "_act_wide", None):
            return
        self._act_wide = wide
        btns = [self.btn_lossless, self.btn_ai, self.btn_preview, self.btn_save]
        for b in btns:
            g.removeWidget(b)
        for i, b in enumerate(btns):
            if wide:
                g.addWidget(b, 0, i)
            else:
                g.addWidget(b, i // 2, i % 2)
        for c in range(4):
            g.setColumnStretch(c, 0)
        stretch = (3, 3, 2, 2) if wide else (1, 1)
        for c, st in enumerate(stretch):
            g.setColumnStretch(c, st)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._set_compact(self.width() < 1000)
        self._reflow_actions()

    def _goto(self, i):
        self.stack.setCurrentIndex(i)
        for k, b in enumerate(self.nav):
            b.setChecked(k == i)
        if i == 3:
            self._refresh_recent()

    # ------------------------------------------------------------ dashboard
    def _card(self, icon, title, desc, accent, handler):
        c = ClickableFrame()
        c.setObjectName("card")
        c.setMinimumHeight(158)
        c.setCursor(Qt.PointingHandCursor)
        c.setStyleSheet(f"#card:hover{{border:1px solid {accent}; background:#16203a;}}")
        c.clicked.connect(handler)
        v = QVBoxLayout(c)
        v.setContentsMargins(18, 16, 18, 16)
        head = QHBoxLayout()
        badge = QLabel(icon)
        badge.setFixedSize(46, 46)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(f"background:{rgba(accent, 0.22)}; border-radius:13px; font-size:22px;")
        t = QLabel(title)
        t.setObjectName("cardTitle")
        head.addWidget(badge)
        head.addSpacing(8)
        head.addWidget(t, 1)
        d = QLabel(desc)
        d.setObjectName("cardDesc")
        d.setWordWrap(True)
        b = QPushButton("Open  →")
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet(f"QPushButton{{background:{accent}; border:none; color:white; font-weight:700; border-radius:9px; padding:8px 16px;}}"
                        f"QPushButton:hover{{background:{QColor(accent).lighter(118).name()};}}")
        b.clicked.connect(handler)
        v.addLayout(head)
        v.addWidget(d, 1)
        v.addWidget(b, 0, Qt.AlignLeft)
        return c

    def _build_dashboard(self):
        banner = QFrame()
        banner.setObjectName("banner")
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(26, 20, 26, 20)
        lg = QLabel()
        lg.setPixmap(QPixmap(resource_path("assets/app.png")).scaled(84, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lg.setStyleSheet("background:transparent;")
        txt = QVBoxLayout()
        t1 = QLabel("What would you like to do today?")
        t1.setObjectName("bannerTitle")
        t1.setWordWrap(True)
        t2 = QLabel("Image → PDF, PDF → Image / Word / Excel, plus optional AI enhancement. Everything stays on this computer.")
        t2.setObjectName("bannerSub")
        t2.setWordWrap(True)
        chips = QHBoxLayout()
        for c in ("🔒 100% Offline", "🛡️ Original Quality", "📝 PDF → Word / Excel", "✨ AI Optional", "⚡ Batch Ready"):
            ch = QLabel(c)
            ch.setObjectName("chip")
            chips.addWidget(ch)
        chips.addStretch()
        txt.addWidget(t1)
        txt.addWidget(t2)
        txt.addSpacing(4)
        txt.addLayout(chips)
        bl.addWidget(lg)
        bl.addSpacing(10)
        bl.addLayout(txt, 1)
        glow(banner, "#6366f1", blur=36, dy=8, alpha=110)

        defs = [
            ("📄", "Image to PDF", "Original-quality conversion. JPEG streams are embedded untouched; nothing is resampled.", "#10b981",
             lambda: self._open_mode("Original (no enhancement)", False)),
            ("✨", "AI Image Enhancer", "Natural photo enhancement, old-photo restoration and JPEG repair.", "#8b5cf6",
             lambda: self._open_mode("Natural Photo Enhancement", True)),
            ("🔍", "AI Upscaler", "2× / 4× upscaling with a local AI model (classical fallback if no model is installed).", "#06b6d4",
             lambda: self._open_mode("Maximum Detail Upscaling", True)),
            ("📑", "Document Clarity", "Faithful scan cleanup and small-text readability. No generative AI on documents.", "#f59e0b",
             lambda: self._open_mode("Scanned Document Clarity", True)),
            ("📦", "Batch Processing", "Create one PDF per image for many files at once.", "#ec4899",
             lambda: self._open_mode("Original (no enhancement)", False, batch=True)),
            ("🖼️", "PDF to Image", "Turn PDF pages into PNG / JPG / TIFF, or pull out the original photos inside a PDF.", "#a855f7",
             lambda: self._open_pdf_tool("image")),
            ("📝", "PDF to Word", "Editable .docx with layout and tables. Scanned PDFs are read with offline OCR.", "#3b82f6",
             lambda: self._open_pdf_tool("word")),
            ("📊", "PDF to Excel", "Tables become Excel sheets. IDs and phone numbers stay safe as text.", "#22c55e",
             lambda: self._open_pdf_tool("excel")),
            ("🕘", "Recent Projects", "Reopen files you created earlier.", "#6366f1", lambda: self._goto(3)),
        ]
        cards = [self._card(*d) for d in defs]
        return DashboardPage(banner, cards)

    def _open_pdf_tool(self, mode):
        self.pdf_tools.set_mode(mode)
        self._goto(2)

    def _open_mode(self, preset, ai_tab, batch=False):
        self._apply_preset(preset)
        self.batch_chk.setChecked(batch)
        self.tabs.setCurrentIndex(0 if ai_tab else 1)
        self._goto(1)

    # ------------------------------------------------------------ workspace
    def _panel(self, title: str = ""):
        f = QFrame()
        f.setObjectName("panel")
        v = QVBoxLayout(f)
        v.setContentsMargins(12, 10, 12, 12)
        v.setSpacing(8)
        if title:
            t = QLabel(title)
            t.setObjectName("panelTitle")
            v.addWidget(t)
        return f, v

    def _build_workspace(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(8)

        # ---- files panel
        fp, fv = self._panel("🖼️  Images  —  drag to add, drag thumbnails to reorder")
        self.list = FileList(self.add_files)
        self.list.currentRowChanged.connect(self._show_selected)
        fv.addWidget(self.list, 1)
        r1 = QHBoxLayout()
        r2 = QHBoxLayout()
        for row, items in ((r1, [("➕  Add files", self._pick_files, "btnAdd"), ("📁  Folder", self._pick_folder, "")]),
                           (r2, [("🗑️  Remove", self._remove_sel, ""), ("🧹  Clear", self._clear, "")])):
            for txt, fn, name in items:
                b = QPushButton(txt)
                if name:
                    b.setObjectName(name)
                b.clicked.connect(fn)
                row.addWidget(b)
        fv.addLayout(r1)
        fv.addLayout(r2)
        fp.setMinimumWidth(160)

        # ---- preview panel
        pp, pv = self._panel("🔎  Preview  —  drag the divider, wheel to zoom")
        self.view = CompareView()
        pv.addWidget(self.view, 1)
        zr = QHBoxLayout()
        for txt, fn in (("Fit", self.view.fit), ("100%", lambda: self.view.set_zoom_percent(100)),
                        ("200%", lambda: self.view.set_zoom_percent(200))):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            zr.addWidget(b)
        self.dim_label = QLabel("")
        self.dim_label.setObjectName("hint")
        self.dim_label.setWordWrap(True)
        zr.addWidget(self.dim_label, 1)
        pv.addLayout(zr)
        self.warn_label = QLabel("")
        self.warn_label.setObjectName("warn")
        self.warn_label.setWordWrap(True)
        pv.addWidget(self.warn_label)
        pp.setMinimumWidth(200)

        # ---- settings panel
        sp, sv = self._panel()
        self.tabs = QTabWidget()
        self.tabs.addTab(scroll(self._tab_enhance()), "✨ Enhance")
        self.tabs.addTab(scroll(self._tab_pdf()), "📄 PDF")
        self.tabs.addTab(scroll(self._tab_advanced()), "⚙️ Advanced")
        sv.addWidget(self.tabs, 1)
        sp.setMinimumWidth(250)

        split.addWidget(fp)
        split.addWidget(pp)
        split.addWidget(sp)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        split.setSizes([250, 620, 360])
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(split)
        holder.setMinimumHeight(300)
        outer.addWidget(scroll(holder), 1)       # panels scroll on small screens ...

        # ---- bottom: status, progress, special buttons
        self.badges = QLabel("Ready")
        self.badges.setObjectName("badge")
        self.badges.setWordWrap(True)
        outer.addWidget(self.badges)
        pr = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.cancel_btn = QPushButton("✖  Cancel")
        self.cancel_btn.setObjectName("btnDanger")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        pr.addWidget(self.progress, 1)
        pr.addWidget(self.cancel_btn)
        outer.addLayout(pr)

        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)
        self.btn_lossless = QPushButton("🛡️   Convert Without Quality Loss")
        self.btn_lossless.setObjectName("btnLossless")
        self.btn_lossless.setToolTip("Original-quality PDF. No AI, no re-encoding, nothing resampled.")
        self.btn_lossless.clicked.connect(self._do_convert)
        self.btn_ai = QPushButton("✨   Enhance with AI + Convert to PDF")
        self.btn_ai.setObjectName("btnAI")
        self.btn_ai.setToolTip("Enhance a copy of each image using the Enhance tab settings, then build the PDF.")
        self.btn_ai.clicked.connect(self._do_enhance_convert)
        for b in (self.btn_lossless, self.btn_ai):
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        glow(self.btn_lossless, "#10b981")
        glow(self.btn_ai, "#a855f7")
        self.btn_preview = QPushButton("👁️  Preview Enhancement (full quality)")
        self.btn_preview.setObjectName("btnPreview")
        self.btn_preview.clicked.connect(self._do_preview)
        self.btn_save = QPushButton("💾  Save Enhanced Image…")
        self.btn_save.setObjectName("btnSave")
        self.btn_save.clicked.connect(self._save_enhanced)
        for b in (self.btn_preview, self.btn_save):
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        g.addWidget(self.btn_lossless, 0, 0)
        g.addWidget(self.btn_ai, 0, 1)
        g.addWidget(self.btn_preview, 1, 0)
        g.addWidget(self.btn_save, 1, 1)
        self._act_grid = g
        outer.addLayout(g)                       # ... but status, progress and the action buttons never scroll away
        return page

    def _tab_enhance(self):
        t = QWidget()
        v = QVBoxLayout(t)
        v.setContentsMargins(4, 8, 4, 8)
        top = QHBoxLayout()
        self.live_chk = QCheckBox("⚡ Live preview")
        self.live_chk.setChecked(True)
        self.live_chk.setToolTip("Updates the preview automatically while you move a slider.")
        self.live_chk.toggled.connect(self._live_request)
        reset = QPushButton("↺  Reset")
        reset.setObjectName("btnReset")
        reset.setToolTip("Reset all sliders to the selected preset")
        reset.clicked.connect(lambda: self._apply_preset(self.preset.currentText()))
        top.addWidget(self.live_chk)
        top.addStretch()
        top.addWidget(reset)
        v.addLayout(top)
        v.addWidget(QLabel("Preset"))
        self.preset = QComboBox()
        self.preset.addItems(list(E.PRESETS))
        self.preset.currentTextChanged.connect(self._apply_preset)
        v.addWidget(self.preset)
        self.preset_note = QLabel("")
        self.preset_note.setWordWrap(True)
        self.preset_note.setObjectName("warn")
        v.addWidget(self.preset_note)
        v.addWidget(QLabel("Upscale (applied on final output)"))
        self.scale = QComboBox()
        self.scale.addItems(["1× (no upscale)", "2×", "4×"])
        v.addWidget(self.scale)
        self.sl_rows = {}
        defs = [("denoise", "Noise reduction", 0, 100, False, "Smooths grain/noise while keeping edges."),
                ("jpeg", "JPEG repair", 0, 100, False, "Reduces blocky artifacts and colour banding from heavy compression."),
                ("sharpen", "Sharpening", 0, 100, False, "Edge-aware sharpening with halo limiting."),
                ("bright", "Brightness", -100, 100, True, "Darker  ←  0  →  brighter"),
                ("contrast", "Contrast", -100, 100, True, "Flatter  ←  0  →  punchier")]
        self.sl = {}
        for k, lbl, lo, hi, signed, tip in defs:
            row = SliderRow(lbl, lo, hi, signed, tip)
            self.sl_rows[k] = row
            self.sl[k] = row.slider
            row.slider.valueChanged.connect(self._live_request)
            v.addWidget(row)
        self.use_ai = QCheckBox("🤖 Use AI upscaling model")
        self.use_ai.setToolTip("Needs the local ONNX model; see README.")
        self.wb = QCheckBox("Auto white balance")
        self.cleanup = QCheckBox("Document background cleanup")
        self.deskew = QCheckBox("Deskew (straighten scan)")
        self.bw = QCheckBox("Black && white document mode")
        for c in (self.use_ai, self.wb, self.cleanup, self.deskew, self.bw):
            c.toggled.connect(self._live_request)
            v.addWidget(c)
        self.model_label = QLabel("")
        self.model_label.setObjectName("hint")
        self.model_label.setWordWrap(True)
        v.addWidget(self.model_label)
        self.live_note = QLabel("")
        self.live_note.setObjectName("hint")
        self.live_note.setWordWrap(True)
        v.addWidget(self.live_note)
        v.addStretch()
        self.scale.currentIndexChanged.connect(lambda _: None)
        self._refresh_model_label()
        return t

    def _tab_pdf(self):
        t = QWidget()
        g = QGridLayout(t)
        g.setContentsMargins(4, 8, 4, 8)
        g.setVerticalSpacing(10)
        self.page = QComboBox()
        self.page.addItems(list(PAGE_SIZES_MM) + ["Custom", "Original"])
        self.cw = QDoubleSpinBox(); self.cw.setRange(20, 2000); self.cw.setValue(210); self.cw.setSuffix(" mm")
        self.ch = QDoubleSpinBox(); self.ch.setRange(20, 2000); self.ch.setValue(297); self.ch.setSuffix(" mm")
        self.orient = QComboBox(); self.orient.addItems(["auto", "portrait", "landscape"])
        self.margin = QDoubleSpinBox(); self.margin.setRange(0, 100); self.margin.setSuffix(" mm")
        self.fit = QComboBox(); self.fit.addItems(["Fit (keep full image)", "Fill page (crops edges)", "Original size by DPI"])
        self.dpi = QSpinBox(); self.dpi.setRange(36, 1200); self.dpi.setValue(300)
        self.exif = QCheckBox("Apply EXIF rotation"); self.exif.setChecked(True)
        rows = [("Page size", self.page), ("Custom width", self.cw), ("Custom height", self.ch), ("Orientation", self.orient),
                ("Margin", self.margin), ("Placement", self.fit), ("DPI (physical size)", self.dpi)]
        for i, (l, wd) in enumerate(rows):
            g.addWidget(QLabel(l), i, 0)
            g.addWidget(wd, i, 1)
        g.addWidget(self.exif, len(rows), 0, 1, 2)
        g.setRowStretch(len(rows) + 1, 1)
        g.setColumnStretch(1, 1)
        return t

    def _tab_advanced(self):
        t = QWidget()
        v = QVBoxLayout(t)
        v.setContentsMargins(4, 8, 4, 8)
        g = QGridLayout()
        g.setVerticalSpacing(10)
        self.embed = QComboBox(); self.embed.addItems(["PNG (lossless)", "JPEG (smaller file)"])
        self.jq = QSpinBox(); self.jq.setRange(60, 100); self.jq.setValue(95)
        self.save_fmt = QComboBox(); self.save_fmt.addItems(["PNG", "JPEG"])
        self.device = QComboBox(); self.device.addItems(["Auto (GPU if available)", "CPU only", "GPU"])
        self.tile = QSpinBox(); self.tile.setRange(64, 1024); self.tile.setSingleStep(64); self.tile.setValue(256)
        rows = [("Enhanced image in PDF", self.embed), ("JPEG quality", self.jq), ("Save image as", self.save_fmt),
                ("AI device", self.device), ("AI tile size (lower = less RAM)", self.tile)]
        for i, (l, wd) in enumerate(rows):
            lab = QLabel(l)
            lab.setWordWrap(True)
            g.addWidget(lab, i, 0)
            g.addWidget(wd, i, 1)
        g.setColumnStretch(1, 1)
        v.addLayout(g)
        self.doc_safe = QCheckBox("Document-safe: never use generative AI")
        self.keep_icc = QCheckBox("Keep embedded ICC colour profile"); self.keep_icc.setChecked(True)
        self.batch_chk = QCheckBox("📦 Batch: one PDF per image")
        for c in (self.doc_safe, self.keep_icc, self.batch_chk):
            v.addWidget(c)
        h = QLabel("Original files are never overwritten or modified.")
        h.setObjectName("hint")
        v.addWidget(h)
        v.addStretch()
        return t

    def _build_recent(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(26, 22, 26, 22)
        title = QLabel("<span style='font-size:22px;font-weight:700;color:white'>🕘  Recent Projects</span>")
        v.addWidget(title)
        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(260)
        self.recent_list.itemDoubleClicked.connect(
            lambda it: QDesktopServices.openUrl(QUrl.fromLocalFile(it.data(Qt.UserRole))))
        v.addWidget(self.recent_list, 1)
        h = QLabel("Double-click to open the PDF.")
        h.setObjectName("hint")
        v.addWidget(h)
        return w

    def _refresh_recent(self):
        self.recent_list.clear()
        for r in recent.load():
            it = QListWidgetItem(f"📄  {r['time']}    {os.path.basename(r['path'])}    ({r['pages']} pages, {r['kind']})")
            it.setData(Qt.UserRole, r["path"])
            self.recent_list.addItem(it)

    # ------------------------------------------------------------ state helpers
    def _refresh_model_label(self):
        if E.ai_model_available():
            self.model_label.setText("AI model: installed ✔")
            self.use_ai.setEnabled(True)
        else:
            self.model_label.setText("AI model: not installed. Upscaling will use classical Lanczos. See README → AI model installation.")
            self.use_ai.setEnabled(False)
            self.use_ai.setChecked(False)

    def _apply_preset(self, name):
        s = E.PRESETS.get(name)
        if not s:
            return
        self.preset.blockSignals(True)
        self.preset.setCurrentText(name)
        self.preset.blockSignals(False)
        self.scale.setCurrentIndex({1: 0, 2: 1, 4: 2}[s.scale])
        self.sl["denoise"].setValue(int(s.denoise * 100))
        self.sl["jpeg"].setValue(int(s.jpeg_repair * 100))
        self.sl["sharpen"].setValue(int(s.sharpen * 100))
        self.sl["bright"].setValue(int(s.brightness * 100))
        self.sl["contrast"].setValue(int(s.contrast * 100))
        self.use_ai.setChecked(s.use_ai_upscale and E.ai_model_available())
        self.wb.setChecked(s.white_balance)
        self.cleanup.setChecked(s.doc_cleanup)
        self.deskew.setChecked(s.deskew)
        self.bw.setChecked(s.bw_mode)
        self.doc_safe.setChecked(s.document_safe)
        self.preset_note.setText(E.PRESET_NOTES.get(name, ""))
        self._live_request()

    def _settings(self) -> E.EnhanceSettings:
        return E.EnhanceSettings(
            scale=[1, 2, 4][self.scale.currentIndex()], use_ai_upscale=self.use_ai.isChecked(),
            denoise=self.sl["denoise"].value() / 100, jpeg_repair=self.sl["jpeg"].value() / 100,
            sharpen=self.sl["sharpen"].value() / 100, brightness=self.sl["bright"].value() / 100,
            contrast=self.sl["contrast"].value() / 100, white_balance=self.wb.isChecked(),
            doc_cleanup=self.cleanup.isChecked(), deskew=self.deskew.isChecked(), bw_mode=self.bw.isChecked(),
            document_safe=self.doc_safe.isChecked(), device=["auto", "cpu", "gpu"][self.device.currentIndex()],
            tile=self.tile.value(), label=self.preset.currentText())

    @staticmethod
    def _is_noop(s: E.EnhanceSettings) -> bool:
        return (s.scale == 1 and not any([s.denoise, s.jpeg_repair, s.sharpen, s.brightness, s.contrast, s.white_balance,
                                          s.doc_cleanup, s.deskew, s.bw_mode]))

    def _pdf_opts(self) -> PdfOptions:
        return PdfOptions(page_size=self.page.currentText(), custom_mm=(self.cw.value(), self.ch.value()),
                          orientation=self.orient.currentText(), margin_mm=self.margin.value(),
                          fit=["fit", "fill", "original"][self.fit.currentIndex()], dpi=self.dpi.value(),
                          apply_exif_rotation=self.exif.isChecked())

    def _busy(self, on):
        for b in (self.btn_lossless, self.btn_ai, self.btn_preview, self.btn_save):
            b.setEnabled(not on)
        self.cancel_btn.setEnabled(on)
        if on:
            self.progress.setValue(0)

    # ------------------------------------------------------------ files
    def _pick_files(self):
        fs, _ = QFileDialog.getOpenFileNames(self, "Add images", "", "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp *.gif)")
        self.add_files(fs)

    def _pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Add folder")
        if d:
            self.add_files([d])

    def add_files(self, paths):
        expanded = []
        for p in paths:
            if os.path.isdir(p):
                for n in sorted(os.listdir(p)):
                    if n.lower().endswith(IMG_EXT):
                        expanded.append(os.path.join(p, n))
            elif p.lower().endswith(IMG_EXT):
                expanded.append(p)
        bad = []
        for p in expanded:
            if any(self.list.item(i).data(Qt.UserRole) == p for i in range(self.list.count())):
                continue
            try:
                im = Image.open(p)
                im.draft("RGB", (192, 192))
                im = ImageOps.exif_transpose(im)
                im.thumbnail((192, 192))
                it = QListWidgetItem(QIcon(pil_to_pixmap(im)), os.path.basename(p))
                it.setData(Qt.UserRole, p)
                it.setToolTip(p)
                self.list.addItem(it)
            except Exception:
                bad.append(os.path.basename(p))
        if bad:
            QMessageBox.warning(self, "Unsupported or corrupted files",
                                "These files could not be opened and were skipped:\n" + "\n".join(bad))
        if self.list.count() and self.list.currentRow() < 0:
            self.list.setCurrentRow(0)

    def _ordered_files(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]

    def _remove_sel(self):
        for it in self.list.selectedItems():
            self.list.takeItem(self.list.row(it))
        if not self.list.count():
            self._clear()

    def _clear(self):
        self.list.clear()
        self.view.set_images(None)
        self.dim_label.setText("")
        self._proxy = None
        self.preview_result = None

    def _show_selected(self, row):
        self.preview_result = None
        self._preview_key = None
        if row < 0:
            return
        p = self.list.item(row).data(Qt.UserRole)
        try:
            im, _ = E.load_image(p)
            self.view.set_images(pil_to_pixmap(im))
            self.dim_label.setText(f"Original: {im.width} × {im.height} px")
        except Exception as e:
            self.dim_label.setText(f"Cannot preview: {e}")
            return
        self._live_request()

    # ------------------------------------------------------------ live preview
    def _live_request(self, *_):
        if not hasattr(self, "live_chk") or not self.live_chk.isChecked() or not hasattr(self, "list"):
            return
        if self.list.count() == 0 or self.list.currentRow() < 0:
            return
        self._live_timer.start()

    def _get_proxy(self, path):
        if self._proxy and self._proxy[0] == path:
            return self._proxy
        im, _ = E.load_image(path)
        full = im.size
        if max(im.size) > LIVE_MAX_SIDE:
            im = im.copy()
            im.thumbnail((LIVE_MAX_SIDE, LIVE_MAX_SIDE), Image.LANCZOS)
        self._proxy = (path, im, pil_to_pixmap(im), full)
        return self._proxy

    def _live_fire(self):
        if self.worker is not None and self.worker.isRunning():
            return                                   # a full job is running; it will refresh afterwards
        if self._live_running:
            self._live_pending = True
            for w in list(self._live_workers):
                w.cancel()
            return
        self._start_live()

    def _start_live(self):
        row = self.list.currentRow()
        if row < 0:
            return
        path = self.list.item(row).data(Qt.UserRole)
        s = replace(self._settings(), scale=1, use_ai_upscale=False)
        try:
            proxy = self._get_proxy(path)
        except Exception as e:
            self.live_note.setText(f"Preview unavailable: {e}")
            return
        if self._is_noop(s):
            self.view.set_images(proxy[2], None, keep_view=True)
            self.live_note.setText("No adjustments applied.")
            return
        self._live_running = True
        self._live_pending = False
        w = Worker(lambda pr, c: E.enhance_image(proxy[1], s, None, c, None))
        self._live_workers.add(w)
        w.done.connect(lambda res, p=path: self._live_done(p, res))
        w.cancelled.connect(self._live_end)
        w.failed.connect(lambda m: (self._live_end(), self.live_note.setText(f"Preview error: {m}")))
        w.finished.connect(lambda w=w: self._live_workers.discard(w))
        w.start()

    def _live_end(self):
        self._live_running = False
        if self._live_pending:
            self._live_pending = False
            QTimer.singleShot(0, self._live_fire)

    def _live_done(self, path, res):
        cur = self.list.currentRow()
        if cur >= 0 and self.list.item(cur).data(Qt.UserRole) == path and self._proxy and self._proxy[0] == path:
            self.view.set_images(self._proxy[2], pil_to_pixmap(res.image), keep_view=True)
            ops = "; ".join(res.operations) or "no changes"
            reduced = " (reduced-size preview)" if max(self._proxy[3]) > LIVE_MAX_SIDE else ""
            self.live_note.setText(f"Live preview{reduced}: {ops}. Use “Preview Enhancement” for full quality.")
        self._live_end()

    # ------------------------------------------------------------ jobs
    def _need_files(self):
        if not self.list.count():
            QMessageBox.information(self, APP_NAME, "Add one or more images first.")
            return False
        return True

    def _choose_output(self, files, batch):
        if batch:
            d = QFileDialog.getExistingDirectory(self, "Choose output folder for PDFs")
            return d or None
        default = os.path.join(os.path.dirname(files[0]), os.path.splitext(os.path.basename(files[0]))[0] + ".pdf")
        p, _ = QFileDialog.getSaveFileName(self, "Save PDF as", default, "PDF (*.pdf)")
        if p and not p.lower().endswith(".pdf"):
            p += ".pdf"
        return p or None

    def _start(self, fn, on_done):
        self._live_timer.stop()
        self._busy(True)
        self.worker = Worker(fn)
        self.worker.progress.connect(self._on_progress)
        self.worker.done.connect(lambda r: (self._busy(False), on_done(r)))
        self.worker.failed.connect(lambda m: (self._busy(False), self.badges.setText("Failed"),
                                              QMessageBox.critical(self, "Error", f"{m}\n\nDetails are in the log folder:\n{log_dir()}")))
        self.worker.cancelled.connect(lambda: (self._busy(False), self.badges.setText("Cancelled — no files were changed"),
                                               self.progress.setValue(0)))
        self.worker.start()

    def _on_progress(self, a, b, msg):
        self.progress.setMaximum(max(b, 1))
        self.progress.setValue(a)
        self.progress.setFormat(f"{msg}  (%v/%m)")

    def _cancel(self):
        if self.worker:
            self.worker.cancel()

    def _do_convert(self):
        if not self._need_files():
            return
        files, batch, opts = self._ordered_files(), self.batch_chk.isChecked(), self._pdf_opts()
        out = self._choose_output(files, batch)
        if not out:
            return
        self._start(lambda pr, c: jobs.convert_original(files, out, opts, batch, pr, c), self._finished_outputs)

    def _memory_ok(self, files, scale):
        if scale <= 1:
            return True
        worst = 0
        for f in files:
            try:
                w, h = Image.open(f).size
                worst = max(worst, estimate_enhance_bytes(w, h, scale))
            except Exception:
                pass
        if worst > 0.7 * available_ram_bytes():
            r = QMessageBox.question(self, "Low memory",
                                     f"Processing the largest image at {scale}× may need ~{worst / 1e9:.1f} GB RAM, "
                                     "more than is safely available.\n\nContinue anyway? (Choose No to lower the upscale factor.)")
            return r == QMessageBox.Yes
        return True

    def _confirm_ai(self, s):
        if s.use_ai_upscale and not s.document_safe and E.ai_model_available() and s.scale > 1:
            r = QMessageBox.question(self, "AI-generated detail",
                                     "AI upscaling can create plausible detail that was not in the original image.\n"
                                     "Do NOT use it on certificates, ID cards, forms or legal papers.\n\nContinue?")
            return r == QMessageBox.Yes
        return True

    def _do_enhance_convert(self):
        if not self._need_files():
            return
        s = self._settings()
        if self._is_noop(s):
            QMessageBox.information(self, APP_NAME, "No enhancement is selected. Choose a preset or move a slider, "
                                                    "or use “Convert Without Quality Loss”.")
            return
        files = self._ordered_files()
        if not self._confirm_ai(s) or not self._memory_ok(files, s.scale):
            return
        batch, opts = self.batch_chk.isChecked(), self._pdf_opts()
        out = self._choose_output(files, batch)
        if not out:
            return
        embed = "jpeg" if self.embed.currentIndex() == 1 else "png"
        jq, icc = self.jq.value(), self.keep_icc.isChecked()
        self._start(lambda pr, c: jobs.enhance_and_convert(files, out, s, opts, batch, embed, jq, icc, pr, c),
                    self._finished_outputs)

    def _finished_outputs(self, outs):
        text = "\n\n".join(
            (("Operations:\n  " + "\n  ".join(o.operations) + "\n") if o.operations else "") +
            (("Warnings:\n  " + "\n  ".join(o.warnings) + "\n") if o.warnings else "") +
            (("Skipped:\n  " + "\n  ".join(o.result.errors) + "\n") if o.result.errors else "") +
            o.report.to_text() for o in outs)
        statuses = []
        for o in outs:
            for st in o.report.statuses:
                if st not in statuses:
                    statuses.append(st)
        self.badges.setText("✔  " + "   •   ".join(statuses))
        self.progress.setValue(self.progress.maximum())
        for o in outs:
            recent.add(o.pdf, "enhanced" if o.operations else "original-quality", len(o.report.pages))
        ReportDialog(self, text, outs[0].pdf).exec()

    def _full_job(self, p, s):
        def job(pr, c):
            im, icc = E.load_image(p)
            return im, E.enhance_image(im, s, pr, c, icc)
        return job

    def _do_preview(self):
        if not self._need_files():
            return
        row = max(self.list.currentRow(), 0)
        p = self.list.item(row).data(Qt.UserRole)
        s = self._settings()
        if self._is_noop(s):
            QMessageBox.information(self, APP_NAME, "Preset is “Original” and sliders are at zero — nothing to preview.")
            return
        if not self._confirm_ai(s) or not self._memory_ok([p], s.scale):
            return
        self._start(self._full_job(p, s), lambda pair, p=p, s=s: self._preview_done(pair, p, s))

    def _preview_done(self, pair, p=None, s=None):
        orig, res = pair
        self.preview_result = res
        self._preview_key = (p, repr(s))
        self.view.set_images(pil_to_pixmap(orig), pil_to_pixmap(res.image))
        self.dim_label.setText(f"Original {res.original_size[0]}×{res.original_size[1]}  →  Enhanced "
                               f"{res.output_size[0]}×{res.output_size[1]} px"
                               + (f"  ({res.scale}×)" if res.scale > 1 else ""))
        self.warn_label.setText("  ".join(res.warnings))
        self.badges.setText("👁️  Full-quality preview — " + ("; ".join(res.operations) or "no changes")
                            + ("   •   AI Enhancement Applied" if res.ai_used else ""))
        self.progress.setValue(self.progress.maximum())

    def _save_enhanced(self):
        if not self._need_files():
            return
        row = max(self.list.currentRow(), 0)
        src = self.list.item(row).data(Qt.UserRole)
        s = self._settings()
        if self._is_noop(s):
            QMessageBox.information(self, APP_NAME, "Nothing to save: no enhancement is selected.")
            return
        if self.preview_result is not None and self._preview_key == (src, repr(s)):
            self._write_enhanced(src)
            return
        if not self._confirm_ai(s) or not self._memory_ok([src], s.scale):
            return

        def done(pair):
            self._preview_done(pair, src, s)
            self._write_enhanced(src)
        self._start(self._full_job(src, s), done)

    def _write_enhanced(self, src):
        fmt = self.save_fmt.currentText()
        ext = ".png" if fmt == "PNG" else ".jpg"
        default = os.path.splitext(src)[0] + "_enhanced" + ext
        p, _ = QFileDialog.getSaveFileName(self, "Save enhanced image (original is kept)", default, f"{fmt} (*{ext})")
        if not p:
            return
        if os.path.abspath(p) == os.path.abspath(src):
            QMessageBox.warning(self, APP_NAME, "Refusing to overwrite the original image. Choose a different name.")
            return
        E.save_image(self.preview_result, p, fmt, self.jq.value(), self.keep_icc.isChecked())
        self.badges.setText(f"💾  Saved enhanced image: {p}   •   Lossless Output Format" if fmt == "PNG"
                            else f"💾  Saved enhanced image: {p}   •   Lossy Conversion Detected (JPEG)")

    def _about(self):
        gpu = ", ".join(gpu_providers()) or "none detected (CPU mode)"
        QMessageBox.information(
            self, "About / Hardware",
            f"{APP_NAME} {APP_VERSION}\n\nAvailable RAM: {available_ram_bytes() / 1e9:.1f} GB\nGPU acceleration: {gpu}\n"
            f"AI model: {'installed' if E.ai_model_available() else 'not installed'}\nModels folder: {E.models_dir()}\n"
            f"Log folder: {log_dir()}\n\nAll processing is local. No network access is used.")

    def closeEvent(self, e):
        for w in list(self._live_workers):
            w.cancel()
            w.wait(2000)
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
        self.pdf_tools.shutdown()
        super().closeEvent(e)
