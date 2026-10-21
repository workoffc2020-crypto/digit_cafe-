"""PDF Tools page: PDF -> Image / Word / Excel (self-contained widget used by MainWindow)."""
from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFrame,
                               QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
                               QSpinBox, QSplitter, QStackedWidget, QTextEdit, QVBoxLayout, QWidget)

from app.core import pdf_convert as C
from app.core import recent
from app.core.logging_setup import log_dir
from app.ui.worker import Worker

MODES = {
    "image": ("🖼️", "PDF → Image", "#8b5cf6", "#ec4899"),
    "word": ("📝", "PDF → Word", "#3b82f6", "#06b6d4"),
    "excel": ("📊", "PDF → Excel", "#10b981", "#84cc16"),
}
PAGE_STYLE = """
QPushButton#modeBtn { padding:13px 10px; font-size:14px; font-weight:700; border-radius:14px;
                      background:#101728; border:2px solid #243055; color:#c3cde8; }
QPushButton#modeBtn:hover { border-color:#3d4d7c; background:#162039; }
QPushButton#modeBtn:disabled { color:#5d6788; }
QLineEdit { background:#141c33; border:1px solid #2a3558; border-radius:8px; padding:6px 9px; min-height:20px; color:#e8ecf6; }
QLineEdit:hover, QLineEdit:focus { border-color:#14b8a6; }
"""


def _scroll(widget: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.NoFrame)
    sa.setWidget(widget)
    return sa


def _panel(title: str = ""):
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


def _pdf_icon(path: str):
    """(QIcon of first page, 'N pages' / 'locked') — never raises."""
    try:
        doc = C.pymupdf.open(path)
        try:
            if doc.needs_pass:
                return QIcon(), "🔒 password protected"
            n = doc.page_count
            pix = doc[0].get_pixmap(dpi=36, alpha=False, colorspace=C.pymupdf.csRGB)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
            return QIcon(QPixmap.fromImage(img)), f"{n} page{'s' if n != 1 else ''}"
        finally:
            doc.close()
    except Exception:
        return QIcon(), "cannot be read"


class PdfList(QListWidget):
    def __init__(self, on_files):
        super().__init__()
        self._on_files = on_files
        self.setIconSize(QSize(40, 52))
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setMinimumHeight(150)
        self.setSpacing(2)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.count() == 0:
            p = QPainter(self.viewport())
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor("#2d3a5e"), 2, Qt.DashLine))
            r = self.viewport().rect().adjusted(12, 12, -12, -12)
            p.drawRoundedRect(r, 14, 14)
            p.setPen(QColor("#8d97b2"))
            p.drawText(r, Qt.AlignCenter, "⬇\n\nDrag && drop PDF files here\nor use  ➕ Add PDFs")

    def dragEnterEvent(self, e):
        e.acceptProposedAction() if e.mimeData().hasUrls() else super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        e.acceptProposedAction() if e.mimeData().hasUrls() else super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self._on_files([u.toLocalFile() for u in e.mimeData().urls()])
            e.acceptProposedAction()


class PdfToolsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(PAGE_STYLE)
        self.worker = None
        self.mode = "image"
        self.last_out = None

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(8)

        title = QLabel("<span style='font-size:20px;font-weight:700;color:white'>PDF Tools</span>"
                       "&nbsp;&nbsp;<span style='color:#7d88a8'>Convert PDFs to pictures, Word or Excel — offline, on this computer.</span>")
        title.setWordWrap(True)
        root.addWidget(title)

        # ---- mode buttons
        mrow = QHBoxLayout()
        mrow.setSpacing(10)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.mode_btns = {}
        for key, (icon, name, c1, c2) in MODES.items():
            b = QPushButton(f"{icon}   {name}")
            b.setObjectName("modeBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            b.setStyleSheet(
                "QPushButton:checked { border:none; color:white; background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"stop:0 {c1},stop:1 {c2}); }}")
            b.clicked.connect(lambda _=False, k=key: self.set_mode(k))
            self.group.addButton(b)
            self.mode_btns[key] = b
            mrow.addWidget(b)
        root.addLayout(mrow)

        # ---- panels: files | options + results
        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(8)

        fp, fv = _panel("📑  PDF files — drag to add")
        fp.setMinimumWidth(230)
        self.list = PdfList(self.add_files)
        fv.addWidget(self.list, 1)
        r1, r2 = QHBoxLayout(), QHBoxLayout()
        for row, items in ((r1, [("➕  Add PDFs", self._pick_files, "btnAdd"), ("📁  Folder", self._pick_folder, "")]),
                           (r2, [("🗑️  Remove", self._remove_sel, ""), ("🧹  Clear", self.list.clear, "")])):
            for txt, fn, name in items:
                b = QPushButton(txt)
                if name:
                    b.setObjectName(name)
                b.clicked.connect(fn)
                row.addWidget(b)
        fv.addLayout(r1)
        fv.addLayout(r2)

        rp, rv = _panel("⚙️  Options")
        rp.setMinimumWidth(300)
        self.opt_stack = QStackedWidget()
        self.opt_stack.addWidget(self._image_options())
        self.opt_stack.addWidget(self._word_options())
        self.opt_stack.addWidget(self._excel_options())
        rv.addWidget(self.opt_stack)
        rv.addWidget(self._common_options())
        self.note = QLabel("")
        self.note.setObjectName("hint")
        self.note.setWordWrap(True)
        rv.addWidget(self.note)
        self.ocr_note = QLabel("")
        self.ocr_note.setObjectName("warn")
        self.ocr_note.setWordWrap(True)
        rv.addWidget(self.ocr_note)
        lbl = QLabel("Results")
        lbl.setObjectName("panelTitle")
        rv.addWidget(lbl)
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setMinimumHeight(120)
        self.results.setPlaceholderText("The conversion report appears here: files created, pages, OCR use, warnings.")
        rv.addWidget(self.results, 1)

        split.addWidget(fp)
        split.addWidget(rp)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([300, 640])
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(split)
        holder.setMinimumHeight(330)
        root.addWidget(_scroll(holder), 1)             # panels scroll on small screens, the action bar below never does

        # ---- pinned action bar
        self.status = QLabel("Ready")
        self.status.setObjectName("badge")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        pr = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.cancel_btn = QPushButton("✖  Cancel")
        self.cancel_btn.setObjectName("btnDanger")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel)
        pr.addWidget(self.progress, 1)
        pr.addWidget(self.cancel_btn)
        root.addLayout(pr)
        ar = QHBoxLayout()
        self.go_btn = QPushButton()
        self.go_btn.setCursor(Qt.PointingHandCursor)
        self.go_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.go_btn.clicked.connect(self.start)
        self.open_btn = QPushButton("📂  Open output folder")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_out)
        ar.addWidget(self.go_btn, 3)
        ar.addWidget(self.open_btn, 1)
        root.addLayout(ar)
        self.eff = QGraphicsDropShadowEffect(self.go_btn)
        self.eff.setBlurRadius(30)
        self.eff.setOffset(0, 5)
        self.go_btn.setGraphicsEffect(self.eff)

        self.set_mode("image")

    # ------------------------------------------------------------ option panels
    def _grid(self):
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setVerticalSpacing(8)
        g.setColumnStretch(1, 1)
        return w, g

    def _image_options(self):
        w, g = self._grid()
        self.img_mode = QComboBox()
        self.img_mode.addItems(["Render pages as pictures", "Extract original embedded images (lossless)"])
        self.img_fmt = QComboBox()
        self.img_fmt.addItems(["PNG (lossless)", "JPG (smaller files)", "TIFF (lossless, for printing)"])
        self.img_dpi = QSpinBox()
        self.img_dpi.setRange(50, 600)
        self.img_dpi.setValue(200)
        self.img_dpi.setSuffix(" DPI")
        self.img_dpi.setToolTip("150 = screen/WhatsApp, 200 = good default, 300 = print, 600 = very large files")
        self.img_q = QSpinBox()
        self.img_q.setRange(60, 100)
        self.img_q.setValue(95)
        rows = [("What to save", self.img_mode), ("Format", self.img_fmt), ("Quality (DPI)", self.img_dpi), ("JPG quality", self.img_q)]
        for i, (l, x) in enumerate(rows):
            g.addWidget(QLabel(l), i, 0)
            g.addWidget(x, i, 1)
        self.img_mode.currentIndexChanged.connect(self._img_mode_changed)
        return w

    def _img_mode_changed(self, i):
        extract = i == 1
        for x in (self.img_fmt, self.img_dpi, self.img_q):
            x.setEnabled(not extract)

    def _ocr_combo(self):
        c = QComboBox()
        c.addItems(["Automatic (only scanned pages)", "Off (never use OCR)", "Always (force OCR on every page)"])
        c.setToolTip("OCR reads text from scanned pictures. Needs no internet.")
        return c

    def _word_options(self):
        w, g = self._grid()
        self.word_ocr = self._ocr_combo()
        self.word_hl = QCheckBox("Highlight uncertain OCR text in yellow")
        self.word_hl.setChecked(True)
        g.addWidget(QLabel("Scanned pages (OCR)"), 0, 0)
        g.addWidget(self.word_ocr, 0, 1)
        g.addWidget(self.word_hl, 1, 0, 1, 2)
        return w

    def _excel_options(self):
        w, g = self._grid()
        self.xl_layout = QComboBox()
        self.xl_layout.addItems(["One sheet per table", "One sheet per page", "Everything on one sheet"])
        self.xl_ocr = self._ocr_combo()
        self.xl_numbers = QCheckBox("Turn clean numbers into Excel numbers")
        self.xl_numbers.setChecked(True)
        self.xl_numbers.setToolTip("1,250.50 becomes a number. Phone/Aadhaar/ID values and 0123 stay text.")
        self.xl_fallback = QCheckBox("If no table is found, arrange the text into columns")
        self.xl_fallback.setChecked(True)
        g.addWidget(QLabel("Sheets"), 0, 0)
        g.addWidget(self.xl_layout, 0, 1)
        g.addWidget(QLabel("Scanned pages (OCR)"), 1, 0)
        g.addWidget(self.xl_ocr, 1, 1)
        g.addWidget(self.xl_numbers, 2, 0, 1, 2)
        g.addWidget(self.xl_fallback, 3, 0, 1, 2)
        return w

    def _common_options(self):
        w, g = self._grid()
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("All pages  —  or e.g. 1-3,5,8-")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Only for password-protected PDFs")
        self.same_dir = QCheckBox("Save in a “Converted” folder next to the first PDF")
        self.same_dir.setChecked(True)
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText("Choose an output folder…")
        self.out_btn = QPushButton("Browse…")
        self.out_btn.clicked.connect(self._browse_out)
        self.same_dir.toggled.connect(self._same_dir_toggled)
        g.addWidget(QLabel("Pages"), 0, 0)
        g.addWidget(self.pages, 0, 1, 1, 2)
        g.addWidget(QLabel("Password"), 1, 0)
        g.addWidget(self.password, 1, 1, 1, 2)
        g.addWidget(self.same_dir, 2, 0, 1, 3)
        g.addWidget(self.out_edit, 3, 0, 1, 2)
        g.addWidget(self.out_btn, 3, 2)
        self._same_dir_toggled(True)
        return w

    def _same_dir_toggled(self, on):
        self.out_edit.setEnabled(not on)
        self.out_btn.setEnabled(not on)

    def _browse_out(self):
        d = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if d:
            self.out_edit.setText(d)

    # ------------------------------------------------------------ mode
    def set_mode(self, mode: str):
        if mode not in MODES:
            return
        self.mode = mode
        icon, name, c1, c2 = MODES[mode]
        self.mode_btns[mode].setChecked(True)
        self.opt_stack.setCurrentIndex(list(MODES).index(mode))
        self.go_btn.setText(f"{icon}   Convert to {name.split('→ ')[1]}")
        self.go_btn.setStyleSheet(
            "QPushButton { border:none; border-radius:14px; font-size:15px; font-weight:700; color:white; padding:15px 18px;"
            f" background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {c1},stop:1 {c2}); }}"
            "QPushButton:hover { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {QColor(c1).lighter(115).name()},stop:1 {QColor(c2).lighter(115).name()}); }}"
            "QPushButton:disabled { background:#232b44; color:#6b7595; }")
        col = QColor(c1)
        col.setAlpha(150)
        self.eff.setColor(col)
        notes = {
            "image": "Render = every page becomes a picture. Extract = the original photos inside the PDF, byte-for-byte (JPEG stays the exact original).",
            "word": "Text PDFs keep layout, fonts and tables. Review the result in Word: very complex designs can still shift a little.",
            "excel": "Tables become sheets. Numbers like 1,250.50 are real numbers; Aadhaar/phone/ID values stay text so nothing is damaged.",
        }
        self.note.setText(notes[mode])
        if mode == "image" or C.ocr_available():
            self.ocr_note.setText("")
        else:
            self.ocr_note.setText("Scanned-PDF reading (OCR) is not installed, so scanned pages cannot be converted to text. "
                                  "Text PDFs work normally. See README → OCR.")
        if mode != "image" and C.ocr_available():
            self.ocr_note.setText("OCR works offline and reads English letters and digits best. Hindi and other scripts are not supported yet.")

    # ------------------------------------------------------------ files
    def _pick_files(self):
        fs, _ = QFileDialog.getOpenFileNames(self, "Add PDF files", "", "PDF files (*.pdf)")
        self.add_files(fs)

    def _pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Add all PDFs from a folder")
        if d:
            self.add_files([d])

    def add_files(self, paths):
        found = []
        for p in paths:
            if os.path.isdir(p):
                found += [os.path.join(p, n) for n in sorted(os.listdir(p)) if n.lower().endswith(".pdf")]
            elif p.lower().endswith(".pdf"):
                found.append(p)
        have = set(self.files())
        skipped = []
        for p in found:
            if p in have:
                continue
            icon, info = _pdf_icon(p)
            it = QListWidgetItem(icon, f"{os.path.basename(p)}\n{info}")
            it.setData(Qt.UserRole, p)
            it.setToolTip(p)
            self.list.addItem(it)
            if info == "cannot be read":
                skipped.append(os.path.basename(p))
        if not found and paths:
            self.status.setText("Only .pdf files can be added here.")
        if skipped:
            QMessageBox.warning(self, "PDF problem", "These files look damaged or are not real PDFs:\n" + "\n".join(skipped)
                                + "\n\nThey stay in the list and will be reported when you convert.")

    def files(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]

    def _remove_sel(self):
        for it in self.list.selectedItems():
            self.list.takeItem(self.list.row(it))

    # ------------------------------------------------------------ run
    def _options(self) -> C.ConvertOptions:
        ocr_map = ["auto", "off", "force"]
        o = C.ConvertOptions(pages=self.pages.text().strip(), password=self.password.text())
        o.image_mode = "extract" if self.img_mode.currentIndex() == 1 else "render"
        o.fmt = ["png", "jpg", "tiff"][self.img_fmt.currentIndex()]
        o.dpi = self.img_dpi.value()
        o.jpeg_quality = self.img_q.value()
        o.ocr = ocr_map[(self.word_ocr if self.mode == "word" else self.xl_ocr).currentIndex()]
        o.highlight_uncertain = self.word_hl.isChecked()
        o.excel_layout = ["sheet_per_table", "sheet_per_page", "single_sheet"][self.xl_layout.currentIndex()]
        o.convert_numbers = self.xl_numbers.isChecked()
        o.text_fallback = self.xl_fallback.isChecked()
        return o

    def _out_dir(self, files):
        if self.same_dir.isChecked():
            return os.path.join(os.path.dirname(files[0]), "Converted")
        return self.out_edit.text().strip()

    def _busy(self, on):
        for b in (self.go_btn, *self.mode_btns.values()):
            b.setEnabled(not on)
        self.cancel_btn.setEnabled(on)
        if on:
            self.progress.setValue(0)

    def start(self):
        if self.worker is not None and self.worker.isRunning():
            return
        files = self.files()
        if not files:
            QMessageBox.information(self, "PDF Tools", "Add one or more PDF files first.")
            return
        out_dir = self._out_dir(files)
        if not out_dir:
            QMessageBox.information(self, "PDF Tools", "Choose an output folder, or tick “Save in a Converted folder”.")
            return
        kind, opts = self.mode, self._options()
        self.last_out = out_dir
        self.results.setPlainText("Working…")
        self.status.setText(f"Converting {len(files)} file{'s' if len(files) != 1 else ''}…")
        self._busy(True)
        self.worker = Worker(lambda pr, c: C.run_batch(kind, files, out_dir, opts, pr, c))
        self.worker.progress.connect(self._on_progress)
        self.worker.done.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.worker.cancelled.connect(self._cancelled)
        self.worker.start()

    def _on_progress(self, a, b, msg):
        self.progress.setMaximum(max(b, 1))
        self.progress.setValue(a)
        self.progress.setFormat(f"{msg}  (%p%)")

    def _done(self, reports):
        self._busy(False)
        ok = [r for r in reports if r.ok]
        bad = [r for r in reports if not r.ok]
        head = f"{len(ok)} of {len(reports)} file{'s' if len(reports) != 1 else ''} converted"
        if bad:
            head += f", {len(bad)} failed"
        self.results.setPlainText(head + "\n" + "=" * 52 + "\n\n" + "\n\n".join(r.to_text() for r in reports))
        warn = any(r.warnings for r in reports)
        self.status.setText(("✔ " if ok and not bad else "⚠ ") + head + ("  —  read the warnings below" if warn or bad else ""))
        self.progress.setValue(self.progress.maximum())
        self.open_btn.setEnabled(bool(ok))
        label = {"image": "pdf→image", "word": "pdf→word", "excel": "pdf→excel"}[self.mode]
        for r in ok:
            target = r.outputs[0] if self.mode != "image" else os.path.dirname(r.outputs[0])
            recent.add(target, label, r.pages_done)

    def _failed(self, msg):
        self._busy(False)
        self.status.setText("Failed")
        QMessageBox.critical(self, "Error", f"{msg}\n\nDetails are in the log folder:\n{log_dir()}")

    def _cancelled(self):
        self._busy(False)
        self.progress.setValue(0)
        self.status.setText("Cancelled — source PDFs were not changed")

    def cancel(self):
        if self.worker:
            self.worker.cancel()

    def _open_out(self):
        if self.last_out and os.path.isdir(self.last_out):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_out))

    def shutdown(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
