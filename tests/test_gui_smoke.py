import os

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("PySide6")


def _jpg(p):
    arr = (np.random.default_rng(3).random((300, 400, 3)) * 255).astype("uint8")
    Image.fromarray(arr).save(p, "JPEG")
    return p


def test_window_loads_and_converts(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog
    from app.ui.main_window import MainWindow, ReportDialog
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    assert not w.windowIcon().isNull()
    f = _jpg(str(tmp_path / "a.jpg"))
    w.add_files([f, str(tmp_path)])
    assert w.list.count() == 1
    out = str(tmp_path / "o.pdf")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (out, "")))
    shown = {}
    monkeypatch.setattr(ReportDialog, "exec", lambda self: shown.setdefault("text", self.findChild(type(self.children()[1])).toPlainText()) or 0)
    w._do_convert()
    w.worker.wait(20000)
    app.processEvents()
    assert os.path.exists(out)
    assert "Original Data Preservation Mode" in w.badges.text()
    assert "Quality Verification Complete" in w.badges.text()


def test_preview_and_noop_guard(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication, QMessageBox
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.add_files([_jpg(str(tmp_path / "a.jpg"))])
    w._apply_preset("Natural Photo Enhancement")
    w._do_preview()
    w.worker.wait(30000)
    app.processEvents()
    assert w.preview_result is not None and w.btn_save.isEnabled()
    assert w.view.right is not None


def _wait(app, w, ms=15000):
    import time
    t = time.time()
    while time.time() - t < ms / 1000:
        app.processEvents()
        if not w._live_running and not w._live_workers and not w._live_timer.isActive():
            break
        time.sleep(0.02)
    app.processEvents()


def test_each_slider_changes_live_preview(tmp_path):
    import numpy as np
    from PySide6.QtWidgets import QApplication
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.add_files([_jpg(str(tmp_path / "a.jpg"))])
    _wait(app, w)
    before = w.view.right
    assert before is None                                  # preset "Original": nothing applied
    seen = []
    for key, val in (("denoise", 60), ("jpeg", 60), ("sharpen", 60), ("bright", 40), ("contrast", 40)):
        w._apply_preset("Original (no enhancement)")
        w.sl[key].setValue(val)
        w._live_timer.stop()
        w._live_fire()
        _wait(app, w)
        assert w.view.right is not None, key              # slider produced an enhanced preview
        a = w.view.left.toImage().constBits().tobytes()
        b = w.view.right.toImage().constBits().tobytes()
        assert a != b, key                                 # ...and it really differs from the original
        seen.append(key)
    assert len(seen) == 5


def test_small_window_keeps_action_buttons_visible(tmp_path):
    from PySide6.QtWidgets import QApplication
    from app.ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.show()
    w._goto(1)
    for W, H in ((1920, 1040), (1366, 768), (1000, 640), (720, 500)):
        w.resize(W, H)
        app.processEvents(); app.processEvents()
        assert w.width() >= 720 and w.height() >= 500
        for b in (w.btn_lossless, w.btn_ai, w.btn_preview, w.btn_save):
            bottom = b.mapTo(w, b.rect().bottomLeft()).y()
            right = b.mapTo(w, b.rect().bottomRight()).x()
            assert bottom <= w.height() and right <= w.width(), (W, H, b.text())
    assert w._compact is True and w.sidebar.width() < 100          # sidebar collapses to icons when narrow
    w.resize(1500, 900); app.processEvents()
    assert w._compact is False
