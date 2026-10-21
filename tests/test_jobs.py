import os

import numpy as np
from PIL import Image

from app.core import jobs
from app.core.enhance import PRESETS, EnhanceSettings
from app.core.pdf_engine import PdfOptions


def _jpg(p, size=(500, 400)):
    arr = (np.random.default_rng(2).random((size[1], size[0], 3)) * 255).astype("uint8")
    Image.fromarray(arr).save(p, "JPEG", quality=90)
    return p


def test_convert_original_batch_and_single(tmp_path):
    files = [_jpg(str(tmp_path / f"{i}.jpg")) for i in range(3)]
    single = jobs.convert_original(files, str(tmp_path / "all.pdf"), PdfOptions())
    assert len(single) == 1 and single[0].report.all_original_preserved
    outdir = tmp_path / "batch"
    outdir.mkdir()
    many = jobs.convert_original(files, str(outdir), PdfOptions(), batch=True)
    assert len(many) == 3 and all(o.report.all_original_preserved for o in many)


def test_enhance_and_convert_reports_truthfully(tmp_path):
    f = _jpg(str(tmp_path / "a.jpg"))
    before = open(f, "rb").read()
    out = jobs.enhance_and_convert([f], str(tmp_path / "e.pdf"), EnhanceSettings(scale=2, sharpen=0.3), PdfOptions())
    o = out[0]
    assert o.report.pages[0].embedded_size == (1000, 800)
    assert "AI/Enhancement Applied" in o.report.statuses
    assert not o.report.all_original_preserved          # must NOT claim original preservation
    assert open(f, "rb").read() == before               # original untouched
    assert o.sizes[0][1] == (500, 400) and o.sizes[0][2] == (1000, 800)


def test_enhance_jpeg_embed_flags_lossy(tmp_path):
    f = _jpg(str(tmp_path / "a.jpg"))
    o = jobs.enhance_and_convert([f], str(tmp_path / "e.pdf"), PRESETS["Natural Photo Enhancement"], PdfOptions(),
                                 embed="jpeg")[0]
    assert any("Lossy" in s for s in o.report.statuses)
