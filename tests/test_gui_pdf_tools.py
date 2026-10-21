import os
import time

import pytest

pytest.importorskip("PySide6")
pymupdf = pytest.importorskip("pymupdf")
reportlab = pytest.importorskip("reportlab")


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    d = tmp_path_factory.mktemp("gui")
    p = str(d / "sample.pdf")
    t = Table([["Item", "Qty", "Price"], ["Notebook", "10", "1,250.50"], ["Pen", "200", "0.75"]])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    st = getSampleStyleSheet()
    SimpleDocTemplate(p, pagesize=A4).build([Paragraph("Sample Report", st["Title"]), Spacer(1, 10), t])
    return p


def _wait(app, page, ms=60000):
    t = time.time()
    while page.worker is not None and page.worker.isRunning() and time.time() - t < ms / 1000:
        app.processEvents()
        time.sleep(0.02)
    page.worker.wait(5000)
    for _ in range(5):
        app.processEvents()


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_navigation_has_pdf_tools_and_recent_still_works():
    from app.ui.main_window import MainWindow
    app = _app()
    w = MainWindow()
    assert [d[1] for d in w.nav_defs] == ["Dashboard", "Image → PDF", "PDF Tools", "Recent Projects"]
    w._goto(2)
    assert w.stack.currentWidget() is w.pdf_tools and w.nav[2].isChecked()
    w._goto(3)
    assert w.stack.currentIndex() == 3 and w.nav[3].isChecked()
    w._open_pdf_tool("excel")
    assert w.pdf_tools.mode == "excel" and w.stack.currentIndex() == 2


@pytest.mark.parametrize("mode,ext", [("image", ".png"), ("word", ".docx"), ("excel", ".xlsx")])
def test_each_mode_converts_through_the_gui(sample_pdf, mode, ext):
    from app.ui.main_window import MainWindow
    app = _app()
    w = MainWindow()
    page = w.pdf_tools
    page.set_mode(mode)
    page.add_files([sample_pdf])
    assert page.list.count() == 1
    page.start()
    _wait(app, page)
    out = os.path.join(os.path.dirname(sample_pdf), "Converted")
    produced = [os.path.join(r, f) for r, _, fs in os.walk(out) for f in fs if f.endswith(ext)]
    assert produced, (mode, page.status.text(), page.results.toPlainText())
    assert "1 of 1 file" in page.results.toPlainText()
    assert page.open_btn.isEnabled() and page.go_btn.isEnabled()


def test_bad_inputs_are_reported_in_the_ui(sample_pdf, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from app.ui.main_window import MainWindow
    app = _app()
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: 0))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: 0))
    w = MainWindow()
    page = w.pdf_tools
    page.set_mode("word")
    junk = tmp_path / "junk.pdf"
    junk.write_bytes(b"not a pdf")
    page.add_files([str(junk), sample_pdf])
    page.pages.setText("7")                                  # beyond the last page
    page.same_dir.setChecked(False)
    page.out_edit.setText(str(tmp_path / "out"))
    page.start()
    _wait(app, page)
    text = page.results.toPlainText()
    assert "0 of 2 files converted, 2 failed" in text and "beyond the last page" in text
    assert page.go_btn.isEnabled()                           # UI is usable again after errors


def test_pdf_tools_fits_small_windows(sample_pdf):
    from app.ui.main_window import MainWindow
    app = _app()
    w = MainWindow()
    w.show()
    w._goto(2)
    for W, H in ((1920, 1040), (1366, 768), (1000, 640), (720, 500)):
        w.resize(W, H)
        app.processEvents(); app.processEvents()
        p = w.pdf_tools
        for b in (p.go_btn, p.open_btn, p.cancel_btn):
            bottom = b.mapTo(w, b.rect().bottomLeft()).y()
            right = b.mapTo(w, b.rect().bottomRight()).x()
            assert bottom <= w.height() and right <= w.width(), (W, H, b.text())
