import os
import sys

from app.core.logging_setup import setup_logging


def selftest() -> int:
    """Headless engine check used to test the PACKAGED executable: CyberCafeStudio.exe --selftest"""
    import tempfile
    import numpy as np
    from PIL import Image
    from app.core.pdf_engine import build_pdf, PdfOptions
    from app.core.verify import verify_pdf
    from app.core.enhance import enhance_image, PRESETS, load_image
    log = []
    ok = True
    try:
        with tempfile.TemporaryDirectory() as t:
            src = os.path.join(t, "a.jpg")
            arr = (np.random.default_rng(1).random((600, 800, 3)) * 255).astype("uint8")
            Image.fromarray(arr).save(src, "JPEG", quality=90)
            out = os.path.join(t, "o.pdf")
            build_pdf([src], out, PdfOptions())
            rep = verify_pdf(out, [src])
            good = rep.all_original_preserved
            log.append(f"original-quality JPEG preserved: {good}")
            im, icc = load_image(src)
            r = enhance_image(im, PRESETS["Natural Photo Enhancement"])
            log.append(f"enhancement ran: {r.operations}")
            from PySide6.QtWidgets import QApplication
            QApplication.instance() or QApplication([])
            log.append("Qt import ok")
            from app.core import pdf_convert as pc
            import pymupdf
            pdf = os.path.join(t, "t.pdf")
            d = pymupdf.open(); pg = d.new_page(); pg.insert_text((72, 100), "Hello 1,250.50 Invoice 0123"); d.save(pdf); d.close()
            conv = {}
            for kind in ("image", "word", "excel"):
                rp = pc.run_batch(kind, [pdf], os.path.join(t, "o_" + kind), pc.ConvertOptions(), lambda *a, **k: None, lambda: False)
                conv[kind] = bool(rp) and all(r.ok for r in rp)
            log.append(f"PDF to image/word/excel: {conv}")
            ocr_ok = pc.ocr_available()
            log.append(f"OCR engine available: {ocr_ok}")
            ok = bool(good and r.operations and all(conv.values()) and ocr_ok)
    except Exception as e:  # noqa
        ok = False
        log.append(f"ERROR: {e!r}")
    from app.core.logging_setup import log_dir
    with open(os.path.join(log_dir(), "selftest.log"), "w", encoding="utf-8") as f:
        f.write(("PASS" if ok else "FAIL") + "\n" + "\n".join(log))
    print("PASS" if ok else "FAIL", *log, sep="\n")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        sys.exit(selftest())
    setup_logging()
    if os.name == "nt":
        try:  # gives the app its own taskbar identity + icon instead of grouping under python.exe
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CyberCafe.Studio.ImagePDF.1")
        except Exception:
            pass
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication
    from app import APP_NAME
    from app.ui.main_window import MainWindow, resource_path

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(resource_path("assets/app.ico")))
    win = MainWindow()
    win.show()
    args = [a for a in sys.argv[1:] if os.path.exists(a)]
    if args:
        win.add_files(args)
        win._goto(1)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
