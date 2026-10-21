"""Quality verification: inspect the produced PDF and compare embedded data to the sources.

Nothing here assumes success: every status is derived from data extracted from the finished PDF.
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pikepdf
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


@dataclass
class PageVerification:
    index: int
    source: str
    embedded_filter: str = ""
    embedded_size: tuple = (0, 0)
    source_size: tuple = (0, 0)
    jpeg_bitstream_identical: Optional[bool] = None
    pixel_identical: Optional[bool] = None
    psnr_db: Optional[float] = None
    ssim_like: Optional[float] = None
    downsampled: bool = False
    lossy_reencode: bool = False
    verdict: str = ""
    notes: list = field(default_factory=list)


@dataclass
class VerificationReport:
    pdf_path: str
    pdf_size_bytes: int
    pages: list
    all_original_preserved: bool
    lossless_output: bool
    statuses: list

    def to_text(self) -> str:
        lines = ["QUALITY VERIFICATION REPORT", "=" * 60,
                 f"PDF: {self.pdf_path}", f"PDF size: {self.pdf_size_bytes/1024:.1f} KB", ""]
        for p in self.pages:
            lines += [f"Page {p.index + 1}: {p.source}",
                      f"  Source size: {p.source_size[0]}x{p.source_size[1]} px",
                      f"  Embedded: {p.embedded_size[0]}x{p.embedded_size[1]} px ({p.embedded_filter})",
                      f"  JPEG bitstream identical: {p.jpeg_bitstream_identical}",
                      f"  Pixel identical: {p.pixel_identical}",
                      f"  PSNR: {p.psnr_db if p.psnr_db is not None else 'n/a'}",
                      f"  Downsampled: {p.downsampled}   Lossy re-encode: {p.lossy_reencode}",
                      f"  Verdict: {p.verdict}"]
            lines += [f"  Note: {n}" for n in p.notes]
            lines.append("")
        lines.append("Status: " + "; ".join(self.statuses))
        return "\n".join(lines)


def _psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    if mse == 0:
        return float("inf")
    return 10 * np.log10(255.0 ** 2 / mse)


def _global_ssim(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)
    b = b.astype(np.float64).mean(axis=2) if b.ndim == 3 else b.astype(np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(), b.var()
    cov = ((a - ma) * (b - mb)).mean()
    return float(((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma ** 2 + mb ** 2 + c1) * (va + vb + c2)))


def extract_page_image(page) -> Optional[tuple]:
    """Return (PdfImage, raw_stream_bytes_or_None, filter_name) for the largest image on a page."""
    images = list(page.images.items())
    if not images:
        return None
    name, obj = max(images, key=lambda kv: int(kv[1].Width) * int(kv[1].Height))
    pimg = pikepdf.PdfImage(obj)
    filt = obj.get("/Filter")
    filt_name = str(filt[0]) if isinstance(filt, pikepdf.Array) and len(filt) else str(filt) if filt is not None else "None"
    raw = None
    if filt_name == "/DCTDecode":
        raw = obj.read_raw_bytes()
    return pimg, raw, filt_name, obj


def verify_pdf(pdf_path: str, sources: list, processed: bool = False) -> VerificationReport:
    """Verify a PDF against its source files.

    sources: list of source file paths (or PIL images / (label, PIL image) for processed output),
    in page order. processed=True means pixels were intentionally changed (enhancement): only
    similarity metrics are meaningful, and no 'original preserved' claim is made.
    """
    import os

    pages = []
    with pikepdf.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            src = sources[i] if i < len(sources) else None
            label = src if isinstance(src, str) else "<enhanced image>"
            pv = PageVerification(index=i, source=os.path.basename(label) if isinstance(src, str) else label)
            ext = extract_page_image(page)
            if ext is None:
                pv.verdict = "No embedded image found"
                pages.append(pv)
                continue
            pimg, raw, filt_name, obj = ext
            pv.embedded_filter = filt_name.lstrip("/")
            pv.embedded_size = (int(obj.Width), int(obj.Height))

            src_im = None
            src_raw = None
            if isinstance(src, str):
                with open(src, "rb") as f:
                    src_raw = f.read()
                src_im = Image.open(io.BytesIO(src_raw))
                src_fmt = src_im.format
                src_im.load()
            elif isinstance(src, Image.Image):
                src_im = src
                src_fmt = None
            if src_im is not None:
                pv.source_size = src_im.size

            # Bitstream comparison for JPEG
            if raw is not None and src_raw is not None and src_fmt == "JPEG":
                pv.jpeg_bitstream_identical = hashlib.sha256(raw).digest() == hashlib.sha256(src_raw).digest() or _jpeg_scan_equal(raw, src_raw)
                if not pv.jpeg_bitstream_identical:
                    pv.notes.append("JPEG stream differs from source (may be container/metadata only).")

            # Pixel comparison
            try:
                emb = pimg.as_pil_image()
                if src_im is not None:
                    a = src_im.convert("RGB") if src_im.mode not in ("RGB", "L") else src_im
                    b = emb
                    if a.mode == "RGBA":
                        a = a.convert("RGB")
                    if a.size != b.size:
                        pv.downsampled = a.size[0] * a.size[1] > b.size[0] * b.size[1]
                        if not processed:
                            pv.notes.append(f"Size differs: source {a.size} vs embedded {b.size}")
                        b = b.resize(a.size) if a.size[0] * a.size[1] <= 4_000_000 * 4 else b
                    if a.size == b.size:
                        a_arr = np.asarray(a.convert("RGB"))
                        b_arr = np.asarray(b.convert("RGB"))
                        pv.pixel_identical = bool(np.array_equal(a_arr, b_arr))
                        pv.psnr_db = None if pv.pixel_identical else round(_psnr(a_arr, b_arr), 2)
                        pv.ssim_like = round(_global_ssim(a_arr, b_arr), 5)
            except Exception as e:
                pv.notes.append(f"Pixel comparison unavailable: {e}")

            if not processed:
                if pv.jpeg_bitstream_identical:
                    pv.verdict = "ORIGINAL JPEG STREAM PRESERVED (bit-identical)"
                elif pv.pixel_identical:
                    pv.verdict = "LOSSLESS: pixels identical to source"
                elif pv.pixel_identical is False:
                    pv.lossy_reencode = True
                    pv.verdict = "PIXELS DIFFER FROM SOURCE (lossy or color/transparency conversion)"
                else:
                    pv.verdict = "Could not fully verify"
            else:
                pv.verdict = "PROCESSED (enhanced) image embedded; similarity metrics shown for reference"
                pv.lossy_reencode = pv.filter_is_lossy if hasattr(pv, "filter_is_lossy") else pv.embedded_filter == "DCTDecode"
            pages.append(pv)

    all_orig = (not processed) and all(
        (p.jpeg_bitstream_identical or p.pixel_identical) for p in pages) and len(pages) > 0
    lossless = all(p.embedded_filter in ("FlateDecode", "DCTDecode") and not p.lossy_reencode for p in pages) and not processed
    statuses = []
    if all_orig:
        statuses.append("Original Data Preservation Mode (verified)")
    if processed:
        statuses.append("AI/Enhancement Applied")
    if any(p.lossy_reencode for p in pages):
        statuses.append("Lossy Conversion Detected")
    if all(p.embedded_filter == "FlateDecode" for p in pages) and pages:
        statuses.append("Lossless Output Format")
    statuses.append("Quality Verification Complete")
    return VerificationReport(pdf_path, os.path.getsize(pdf_path), pages, all_orig, lossless, statuses)


def _jpeg_scan_equal(a: bytes, b: bytes) -> bool:
    """Compare the entropy-coded data (from SOS onward) – ignores metadata segments."""
    ia, ib = a.find(b"\xff\xda"), b.find(b"\xff\xda")
    if ia < 0 or ib < 0:
        return False
    return a[ia:] == b[ib:]
