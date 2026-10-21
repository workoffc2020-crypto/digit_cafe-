from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    progress = Signal(int, int, str)
    done = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, fn):
        super().__init__()
        self._fn = fn
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def is_cancelled(self) -> bool:
        return self._cancel

    def run(self):
        from app.core.enhance import Cancelled as C1
        from app.core.pdf_engine import Cancelled as C2
        import logging
        try:
            res = self._fn(lambda a, b, m: self.progress.emit(a, b, m), self.is_cancelled)
            self.done.emit(res)
        except (C1, C2):
            self.cancelled.emit()
        except MemoryError:
            logging.getLogger("ccs").exception("Out of memory")
            self.failed.emit("Not enough memory. Use a smaller upscale factor or close other programs.")
        except Exception as e:
            logging.getLogger("ccs").exception("Job failed")
            self.failed.emit(str(e))
