"""High-level jobs used by the GUI (and testable without it)."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field

from PIL import Image

from . import enhance as E
from .pdf_engine import PdfOptions, build_pdf
from .verify import verify_pdf


@dataclass
class JobOutput:
    pdf: str
    result: object
    report: object
    operations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    sizes: list = field(default_factory=list)  # (name, orig_size, out_size)


def _groups(files, batch):
    return [[f] for f in files] if batch else [list(files)]


def _out_path(files, out, batch, idx):
    if not batch:
        return out
    base = os.path.splitext(os.path.basename(files[0]))[0]
    return os.path.join(out, base + ".pdf")


def convert_original(files, out, opts: PdfOptions, batch=False, progress=None, cancel=None) -> list:
    """MODE A: original-quality conversion. No pixel-changing operation is ever applied here."""
    outputs = []
    groups = _groups(files, batch)
    for gi, g in enumerate(groups):
        path = _out_path(g, out, batch, gi)
        res = build_pdf(g, path, opts, progress, cancel)
        good = [f for f in g if os.path.basename(f) in {os.path.basename(p.source) for p in res.pages}]
        rep = verify_pdf(path, good)
        outputs.append(JobOutput(path, res, rep,
                                 sizes=[(os.path.basename(p.source), p.source_size, p.embedded_size) for p in res.pages]))
    return outputs


def enhance_and_convert(files, out, settings: E.EnhanceSettings, opts: PdfOptions, batch=False,
                        embed="png", jpeg_quality=95, keep_icc=True, progress=None, cancel=None) -> list:
    """MODE B: enhance each image (originals untouched), then build PDF from the enhanced pixels."""
    outputs = []
    with tempfile.TemporaryDirectory(prefix="ccs_") as tmp:
        for gi, g in enumerate(_groups(files, batch)):
            path = _out_path(g, out, batch, gi)
            items, ops, warns, sizes = [], [], [], []
            for i, f in enumerate(g):
                if cancel and cancel():
                    raise E.Cancelled()
                try:
                    im, icc = E.load_image(f)
                except Exception as e:
                    warns.append(f"{os.path.basename(f)} skipped: {e}")
                    continue
                r = E.enhance_image(im, settings, lambda a, b, m, _i=i: progress and progress(_i, len(g), m), cancel, icc)
                ops += [f"{os.path.basename(f)}: {o}" for o in r.operations]
                warns += list(dict.fromkeys(r.warnings))
                sizes.append((os.path.basename(f), r.original_size, r.output_size))
                if embed == "jpeg":
                    p = os.path.join(tmp, f"{gi}_{i}.jpg")
                    E.save_image(r, p, "JPEG", jpeg_quality, keep_icc)
                    items.append(p)
                else:
                    p = os.path.join(tmp, f"{gi}_{i}.png")
                    E.save_image(r, p, "PNG", keep_icc=keep_icc)
                    items.append(p)
            if not items:
                raise ValueError("No images could be processed. " + "; ".join(warns))
            res = build_pdf(items, path, opts, None, cancel)
            rep = verify_pdf(path, [Image.open(p).copy() for p in items], processed=True)
            for pg, (name, _, _) in zip(rep.pages, sizes):
                pg.source = name + " (enhanced)"
            if embed == "jpeg":
                rep.statuses.append("Lossy Conversion Detected (JPEG embed chosen)")
            outputs.append(JobOutput(path, res, rep, ops, warns, sizes))
    return outputs
