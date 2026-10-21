"""Original-quality image -> PDF engine.

Rules:
  * JPEG (RGB/Gray, non-CMYK) is embedded byte-for-byte via img2pdf (no re-encode).
  * PNG / other lossless formats are embedded losslessly (Flate), never converted to JPEG.
  * Transparency is flattened onto white ONLY when required (PDF image without alpha); this is reported.
  * Pixel data is never resampled. Page layout only scales the placement, not the image data.
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

import img2pdf
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None

PAGE_SIZES_MM = {
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A5": (148.0, 210.0),
    "Letter": (215.9, 279.4),
    "Legal": (215.9, 355.6),
}
MM_PER_PT = 25.4 / 72.0


@dataclass
class PdfOptions:
    page_size: str = "A4"          # A4/A3/A5/Letter/Legal/Custom/Original
    custom_mm: tuple = (210.0, 297.0)
    orientation: str = "auto"      # auto/portrait/landscape
    margin_mm: float = 0.0
    fit: str = "fit"               # fit (keep aspect) / fill (cover, crops) / original (use DPI)
    dpi: int = 300                 # used for "Original" page size / fit == original
    apply_exif_rotation: bool = True


@dataclass
class ImageReport:
    source: str
    source_format: str = ""
    source_size: tuple = (0, 0)
    embedded_size: tuple = (0, 0)
    embedded_format: str = ""
    page_size_mm: tuple = (0.0, 0.0)
    jpeg_stream_preserved: Optional[bool] = None
    resampled: bool = False
    lossy_reencode: bool = False
    color_conversion: str = "none"
    transparency_changed: bool = False
    exif_rotation_applied: bool = False
    notes: list = field(default_factory=list)


@dataclass
class PdfResult:
    output: str
    pages: list
    size_bytes: int
    errors: list = field(default_factory=list)


class Cancelled(Exception):
    pass


def _exif_orientation(im: Image.Image) -> int:
    try:
        return im.getexif().get(0x0112, 1) or 1
    except Exception:
        return 1


def _prepare(path_or_img, opts: PdfOptions):
    """Return (bytes_for_img2pdf, report_partial, rotation_applied).

    Strategy: if no change is needed, pass the original file bytes untouched.
    """
    rep = ImageReport(source=path_or_img if isinstance(path_or_img, str) else "<memory>")
    if isinstance(path_or_img, Image.Image):
        im = path_or_img
        raw = None
    else:
        with open(path_or_img, "rb") as f:
            raw = f.read()
        im = Image.open(io.BytesIO(raw))
    fmt = (im.format or "").upper()
    rep.source_format = fmt or "MEMORY"
    rep.source_size = im.size
    mode = im.mode
    orient = _exif_orientation(im) if opts.apply_exif_rotation else 1
    needs_rotate = orient in (2, 3, 4, 5, 6, 7, 8)

    # --- JPEG: embed original stream unless CMYK or rotation needed (rotation uses PDF /Rotate if possible)
    if raw is not None and fmt == "JPEG" and mode in ("RGB", "L"):
        rep.embedded_format = "JPEG (original stream)"
        rep.embedded_size = im.size
        rep.jpeg_stream_preserved = True
        rot = {3: 180, 6: 90, 8: 270}.get(orient, 0) if needs_rotate else 0
        if needs_rotate and orient not in (3, 6, 8):
            # mirrored orientations: lossless embed is still possible, orientation ignored; note it
            rep.notes.append("Mirrored EXIF orientation not applied to keep JPEG stream untouched.")
        if rot:
            rep.exif_rotation_applied = True
            rep.notes.append(f"EXIF orientation applied via PDF rotation ({rot}°), no pixel change.")
        return raw, rep, rot
    if raw is not None and fmt == "JPEG" and mode == "CMYK":
        rep.embedded_format = "JPEG CMYK (original stream)"
        rep.embedded_size = im.size
        rep.jpeg_stream_preserved = True
        rep.color_conversion = "none (CMYK preserved)"
        return raw, rep, 0

    # --- Lossless formats: re-save as PNG only if img2pdf cannot take them directly
    if raw is not None and fmt in ("PNG",) and "A" not in mode and mode not in ("LA", "RGBA", "P"):
        if mode in ("RGB", "L", "1") or mode.startswith("I;16") is False:
            rep.embedded_format = "PNG (lossless)"
            rep.embedded_size = im.size
            rep.jpeg_stream_preserved = None
            return raw, rep, 0

    # General path: decode, fix transparency if needed, encode PNG losslessly.
    im.load()
    if needs_rotate and opts.apply_exif_rotation:
        im = ImageOps.exif_transpose(im)
        rep.exif_rotation_applied = True
        rep.notes.append("EXIF orientation applied to pixels (lossless transpose).")
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[3])
        im = bg
        rep.transparency_changed = True
        rep.color_conversion = "RGBA -> RGB on white background"
    elif im.mode == "P":
        im = im.convert("RGB")
        rep.color_conversion = "palette -> RGB (lossless)"
    elif im.mode not in ("RGB", "L", "1", "CMYK"):
        im = im.convert("RGB")
        rep.color_conversion = f"{mode} -> RGB"
    buf = io.BytesIO()
    save_kwargs = {}
    icc = im.info.get("icc_profile")
    if icc:
        save_kwargs["icc_profile"] = icc
    im.save(buf, "PNG", compress_level=6, **save_kwargs)
    rep.embedded_format = "PNG (lossless, re-packed)"
    rep.embedded_size = im.size
    return buf.getvalue(), rep, 0


def _page_for(w_px: int, h_px: int, opts: PdfOptions):
    """Return (page_w_pt, page_h_pt, image_w_pt, image_h_pt, x, y) in points."""
    dpi = max(opts.dpi, 1)
    native_w = w_px * 72.0 / dpi
    native_h = h_px * 72.0 / dpi
    margin = opts.margin_mm / MM_PER_PT
    if opts.page_size == "Original":
        return native_w + 2 * margin, native_h + 2 * margin, native_w, native_h, margin, margin
    if opts.page_size == "Custom":
        pw_mm, ph_mm = opts.custom_mm
    else:
        pw_mm, ph_mm = PAGE_SIZES_MM.get(opts.page_size, PAGE_SIZES_MM["A4"])
    pw, ph = pw_mm / MM_PER_PT, ph_mm / MM_PER_PT
    orient = opts.orientation
    if orient == "auto":
        orient = "landscape" if w_px > h_px else "portrait"
    if orient == "landscape" and pw < ph:
        pw, ph = ph, pw
    elif orient == "portrait" and pw > ph:
        pw, ph = ph, pw
    avail_w, avail_h = max(pw - 2 * margin, 1), max(ph - 2 * margin, 1)
    if opts.fit == "original":
        iw, ih = native_w, native_h
        if iw > avail_w or ih > avail_h:
            s = min(avail_w / iw, avail_h / ih)
            iw, ih = iw * s, ih * s
    elif opts.fit == "fill":
        s = max(avail_w / native_w, avail_h / native_h)
        iw, ih = native_w * s, native_h * s
    else:
        s = min(avail_w / native_w, avail_h / native_h)
        iw, ih = native_w * s, native_h * s
    x = (pw - iw) / 2.0
    y = (ph - ih) / 2.0
    return pw, ph, iw, ih, x, y


def build_pdf(
    images: list,
    output: str,
    opts: Optional[PdfOptions] = None,
    progress: Optional[Callable[[int, int, str], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
    skip_bad: bool = True,
) -> PdfResult:
    """Create a PDF from file paths (or PIL images). Original files are never modified."""
    opts = opts or PdfOptions()
    reports, errors, parts = [], [], []
    total = len(images)
    for i, item in enumerate(images):
        if cancel and cancel():
            raise Cancelled()
        name = item if isinstance(item, str) else "<enhanced image>"
        if progress:
            progress(i, total, f"Preparing {os.path.basename(name)}")
        try:
            data, rep, rot = _prepare(item, opts)
            im = Image.open(io.BytesIO(data))
            wpx, hpx = im.size
            if rot in (90, 270):
                eff_w, eff_h = hpx, wpx
            else:
                eff_w, eff_h = wpx, hpx
            pw, ph, iw, ih, x, y = _page_for(eff_w, eff_h, opts)
            rep.page_size_mm = (round(pw * MM_PER_PT, 2), round(ph * MM_PER_PT, 2))
            if opts.fit == "fill" and opts.page_size != "Original":
                rep.notes.append("Fill mode crops image edges at page boundary (pixels unchanged).")
            parts.append((data, rot, pw, ph, iw, ih, x, y))
            reports.append(rep)
        except Exception as e:  # corrupted / unsupported
            msg = f"{os.path.basename(str(name))}: {e}"
            errors.append(msg)
            if not skip_bad:
                raise

    if not parts:
        raise ValueError("No valid images to convert. " + "; ".join(errors))

    # Build each page individually and merge, so per-page layout is exact.
    import pikepdf

    final = pikepdf.Pdf.new()
    for k, (data, rot, pw, ph, iw, ih, x, y) in enumerate(parts):
        if cancel and cancel():
            raise Cancelled()
        # When a PDF /Rotate is used, lay the image out unrotated on a swapped page.
        if rot in (90, 270):
            lw, lh, liw, lih = ph, pw, ih, iw
        else:
            lw, lh, liw, lih = pw, ph, iw, ih

        def layout_fun(imgwidthpx, imgheightpx, ndpi, _a=(lw, lh, liw, lih)):
            return _a

        try:
            pdf_bytes = img2pdf.convert(data, layout_fun=layout_fun)
        except Exception as e:
            im = Image.open(io.BytesIO(data)).convert("RGB")
            b = io.BytesIO()
            im.save(b, "PNG")
            pdf_bytes = img2pdf.convert(b.getvalue(), layout_fun=layout_fun)
            reports[k].notes.append(f"Direct embed failed ({e}); lossless PNG fallback used.")
            reports[k].jpeg_stream_preserved = False
        page_pdf = pikepdf.Pdf.open(io.BytesIO(pdf_bytes))
        if rot:
            page_pdf.pages[0].Rotate = rot
        final.pages.extend(page_pdf.pages)
        if progress:
            progress(k + 1, len(parts), f"Added page {k + 1}")

    os.makedirs(os.path.dirname(os.path.abspath(output)) or ".", exist_ok=True)
    tmp = output + ".part"
    final.save(tmp)
    os.replace(tmp, output)
    return PdfResult(output=output, pages=reports, size_bytes=os.path.getsize(output), errors=errors)
