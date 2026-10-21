import io
import os

import numpy as np
import pikepdf
import pytest
from PIL import Image, ImageDraw

from app.core.pdf_engine import PdfOptions, build_pdf, Cancelled
from app.core.verify import verify_pdf


def _photo(path, size=(1600, 1200), exif_orient=None, icc=False, quality=92):
    rng = np.random.default_rng(1)
    arr = (rng.random((size[1], size[0], 3)) * 255).astype("uint8")
    im = Image.fromarray(arr)
    kw = {"quality": quality}
    if exif_orient:
        ex = Image.Exif(); ex[0x0112] = exif_orient; kw["exif"] = ex
    im.save(path, "JPEG", **kw)
    return path


def _form(path):
    im = Image.new("RGB", (1240, 1754), "white")
    d = ImageDraw.Draw(im)
    for y in range(100, 1700, 40):
        d.line([(80, y), (1160, y)], fill="black", width=1)
        d.text((90, y - 12), "Name: ABCDEF 0123456789", fill="black")
    im.save(path, "PNG")
    return path


def test_jpeg_bitstream_preserved(tmp_path):
    src = _photo(str(tmp_path / "a.jpg"))
    out = str(tmp_path / "o.pdf")
    res = build_pdf([src], out)
    rep = verify_pdf(out, [src])
    assert rep.pages[0].jpeg_bitstream_identical is True
    assert rep.all_original_preserved
    assert rep.pages[0].embedded_size == (1600, 1200)
    assert res.pages[0].jpeg_stream_preserved is True


def test_png_lossless_pixels(tmp_path):
    src = _form(str(tmp_path / "f.png"))
    out = str(tmp_path / "o.pdf")
    build_pdf([src], out)
    rep = verify_pdf(out, [src])
    assert rep.pages[0].pixel_identical is True
    assert "Lossless Output Format" in rep.statuses


def test_transparent_png_reported(tmp_path):
    p = str(tmp_path / "t.png")
    Image.new("RGBA", (200, 200), (255, 0, 0, 128)).save(p)
    out = str(tmp_path / "o.pdf")
    res = build_pdf([p], out)
    assert res.pages[0].transparency_changed is True
    assert os.path.getsize(out) > 0


def test_exif_rotation_no_pixel_change(tmp_path):
    src = _photo(str(tmp_path / "r.jpg"), size=(800, 400), exif_orient=6)
    out = str(tmp_path / "o.pdf")
    res = build_pdf([src], out)
    assert res.pages[0].jpeg_stream_preserved is True
    with pikepdf.open(out) as pdf:
        pg = pdf.pages[0]
        assert int(pg.get("/Rotate", 0)) == 90
        w, h = float(pg.MediaBox[2]), float(pg.MediaBox[3])
    assert w > 0 and h > 0


def test_multi_image_batch_and_a4(tmp_path):
    srcs = [_photo(str(tmp_path / f"{i}.jpg"), size=(900 + i * 10, 700)) for i in range(4)]
    srcs.append(_form(str(tmp_path / "f.png")))
    out = str(tmp_path / "o.pdf")
    res = build_pdf(srcs, out, PdfOptions(page_size="A4", margin_mm=10))
    with pikepdf.open(out) as pdf:
        assert len(pdf.pages) == 5
    assert len(res.pages) == 5
    assert all(abs(min(p.page_size_mm) - 210) < 1 for p in res.pages)


def test_corrupted_file_skipped(tmp_path):
    good = _photo(str(tmp_path / "g.jpg"))
    bad = str(tmp_path / "bad.jpg")
    open(bad, "wb").write(b"not an image")
    res = build_pdf([bad, good], str(tmp_path / "o.pdf"))
    assert len(res.errors) == 1 and len(res.pages) == 1


def test_all_corrupt_raises(tmp_path):
    bad = str(tmp_path / "bad.jpg")
    open(bad, "wb").write(b"nope")
    with pytest.raises(ValueError):
        build_pdf([bad], str(tmp_path / "o.pdf"))


def test_cancel(tmp_path):
    src = _photo(str(tmp_path / "a.jpg"))
    with pytest.raises(Cancelled):
        build_pdf([src, src], str(tmp_path / "o.pdf"), cancel=lambda: True)
    assert not os.path.exists(str(tmp_path / "o.pdf"))


def test_very_large_image(tmp_path):
    p = str(tmp_path / "big.png")
    Image.new("L", (9000, 9000), 200).save(p)
    out = str(tmp_path / "o.pdf")
    build_pdf([p], out)
    rep = verify_pdf(out, [p])
    assert rep.pages[0].embedded_size == (9000, 9000)


def test_original_file_never_modified(tmp_path):
    src = _photo(str(tmp_path / "a.jpg"))
    before = open(src, "rb").read()
    build_pdf([src], str(tmp_path / "o.pdf"))
    assert open(src, "rb").read() == before
