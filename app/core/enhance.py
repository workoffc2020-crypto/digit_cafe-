"""Enhancement engine: classical image processing + optional local ONNX super-resolution.

Design rules:
  * The source image is never modified; every function returns a new array.
  * Presets for official documents never use generative AI (only faithful classical ops).
  * Every applied step is recorded in EnhanceResult.operations so the UI/report only shows true statuses.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field, replace
from typing import Callable, Optional

import cv2
import numpy as np
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None

MODEL_FILENAME = "realesrgan_x4.onnx"


class Cancelled(Exception):
    pass


def models_dir() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.join(os.path.dirname(sys.executable), "models")
        if os.path.isdir(base):
            return base
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cand = os.path.join(here, "models")
    os.makedirs(cand, exist_ok=True)
    return cand


def model_path() -> str:
    return os.path.join(models_dir(), MODEL_FILENAME)


def ai_model_available() -> bool:
    return os.path.isfile(model_path())


@dataclass
class EnhanceSettings:
    scale: int = 1                 # 1, 2, 4
    use_ai_upscale: bool = False   # requires ONNX model; else classical Lanczos
    denoise: float = 0.0           # 0..1
    jpeg_repair: float = 0.0       # 0..1
    sharpen: float = 0.0           # 0..1
    brightness: float = 0.0        # -1..1
    contrast: float = 0.0          # -1..1
    white_balance: bool = False
    doc_cleanup: bool = False      # background normalisation (keeps ink, stamps)
    deskew: bool = False
    bw_mode: bool = False          # optional black & white document mode
    document_safe: bool = False    # forbids generative AI
    device: str = "auto"           # auto / cpu / gpu
    tile: int = 256
    label: str = "Custom"


PRESETS = {
    "Original (no enhancement)": EnhanceSettings(label="Original"),
    "Natural Photo Enhancement": EnhanceSettings(scale=1, denoise=0.25, sharpen=0.35, contrast=0.08, label="Natural Photo"),
    "Maximum Detail Upscaling": EnhanceSettings(scale=4, use_ai_upscale=True, denoise=0.15, sharpen=0.25, label="Maximum Detail"),
    "Old Photo Restoration": EnhanceSettings(scale=2, use_ai_upscale=True, denoise=0.45, jpeg_repair=0.4, sharpen=0.3,
                                             contrast=0.15, white_balance=True, label="Old Photo"),
    "Scanned Document Clarity": EnhanceSettings(scale=1, denoise=0.15, sharpen=0.45, doc_cleanup=True, contrast=0.1,
                                                document_safe=True, label="Document Clarity"),
    "Small Text Readability": EnhanceSettings(scale=2, sharpen=0.6, doc_cleanup=True, contrast=0.15, document_safe=True,
                                              label="Small Text"),
    "Screenshot and Graphics": EnhanceSettings(scale=2, sharpen=0.2, label="Screenshot"),
    "Low-Quality JPEG Repair": EnhanceSettings(scale=1, jpeg_repair=0.7, denoise=0.2, sharpen=0.2, label="JPEG Repair"),
}

PRESET_NOTES = {
    "Maximum Detail Upscaling": "AI upscaling can invent plausible detail that was not in the original. Do not use on official documents.",
    "Old Photo Restoration": "AI upscaling can invent plausible detail. For photographs only.",
    "Scanned Document Clarity": "Faithful mode: no generative AI. Ink, stamps and signatures are preserved.",
    "Small Text Readability": "Faithful mode: classical upscaling only. No characters are generated or changed.",
}


@dataclass
class EnhanceResult:
    image: Image.Image
    operations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    original_size: tuple = (0, 0)
    output_size: tuple = (0, 0)
    scale: int = 1
    ai_used: bool = False
    icc_profile: Optional[bytes] = None


def load_image(path: str) -> tuple:
    """Load an image applying EXIF orientation; returns (PIL RGB/L image, icc_profile)."""
    im = Image.open(path)
    icc = im.info.get("icc_profile")
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[3])
        im = bg
    elif im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    im.load()
    return im, icc


# ---------------------------------------------------------------- classical ops
def _to_bgr(im: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.asarray(im.convert("RGB")), cv2.COLOR_RGB2BGR)


def _to_pil(bgr: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def jpeg_repair(bgr: np.ndarray, strength: float) -> np.ndarray:
    """Remove JPEG blocking / mosquito noise.

    Strong smoothing is applied only where the local gradient is weak (block borders, flat areas, ringing halos);
    real edges such as text strokes, lines and stamps have a strong gradient and are protected by a soft mask.
    """
    strength = float(np.clip(strength, 0, 1))
    if strength <= 0:
        return bgr
    sc = 25 + 75 * strength
    sp = 3 + 5 * strength
    smooth = cv2.bilateralFilter(bgr, d=9, sigmaColor=sc, sigmaSpace=sp)
    if strength > 0.45:
        smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=sc, sigmaSpace=sp)
    if strength > 0.8:
        smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=sc, sigmaSpace=sp)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gray = cv2.GaussianBlur(gray, (0, 0), 0.8)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    t0, t1 = 60.0, 160.0           # gradient (0..~1000): below t0 = flat/blocking, above t1 = real edge
    mask = np.clip((mag - t0) / (t1 - t0), 0, 1)
    mask = cv2.GaussianBlur(mask, (0, 0), 1.0)[..., None]
    return np.clip(bgr * mask + smooth * (1 - mask), 0, 255).astype(np.uint8)


def denoise(bgr: np.ndarray, strength: float, cancel: Optional[Callable[[], bool]] = None) -> np.ndarray:
    """Non-local-means noise reduction with a smooth strength ramp.

    Large images are processed in overlapping horizontal strips so memory/time stay bounded and the job can be
    cancelled between strips.
    """
    strength = float(np.clip(strength, 0, 1))
    if strength <= 0:
        return bgr
    h = 9.5 * strength ** 0.8 + 1.5 * min(1.0, strength * 10)   # 0.1 -> ~3, 0.3 -> ~5, 0.6 -> ~8.7, 1.0 -> 11
    H, W = bgr.shape[:2]
    if H * W <= 2_500_000:
        return cv2.fastNlMeansDenoisingColored(bgr, None, h, h, 5, 15)
    rows = max(256, 2_000_000 // max(W, 1))
    pad = 24
    out = np.empty_like(bgr)
    for y0 in range(0, H, rows):
        if cancel and cancel():
            raise Cancelled()
        y1 = min(y0 + rows, H)
        ya, yb = max(y0 - pad, 0), min(y1 + pad, H)
        piece = cv2.fastNlMeansDenoisingColored(np.ascontiguousarray(bgr[ya:yb]), None, h, h, 5, 15)
        out[y0:y1] = piece[y0 - ya:y0 - ya + (y1 - y0)]
    return out


def sharpen(bgr: np.ndarray, strength: float) -> np.ndarray:
    """Edge-aware unsharp mask on luminance: noise-gated, with overshoot (halo/ringing) limiting."""
    strength = float(np.clip(strength, 0, 1))
    if strength <= 0:
        return bgr
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y = ycc[..., 0].astype(np.float32)
    sigma = 0.8 + 1.2 * strength
    detail = y - cv2.GaussianBlur(y, (0, 0), sigma)
    gate = 1.2                                   # ignore tiny differences (noise) instead of amplifying them
    detail = np.sign(detail) * np.maximum(np.abs(detail) - gate, 0.0)
    amount = 0.6 + 2.4 * strength
    sharp = y + amount * detail
    k = np.ones((5, 5), np.uint8)                # halo limiter: stay near the local min/max
    lo, hi = cv2.erode(y, k), cv2.dilate(y, k)
    margin = 6.0 + 30.0 * strength
    sharp = np.clip(sharp, lo - margin, hi + margin)
    ycc[..., 0] = np.clip(sharp, 0, 255).astype(np.uint8)
    return cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR)


def color_adjust(bgr: np.ndarray, brightness: float, contrast: float, white_balance: bool) -> np.ndarray:
    out = bgr.astype(np.float32)
    if white_balance:
        means = out.reshape(-1, 3).mean(axis=0)
        gain = means.mean() / np.maximum(means, 1e-3)
        gain = np.clip(gain, 0.8, 1.25)  # limit to avoid colour casts
        out = out * gain
    if contrast:
        c = 1.0 + float(np.clip(contrast, -1, 1))
        out = (out - 127.5) * c + 127.5
    if brightness:
        out = out + 80.0 * float(np.clip(brightness, -1, 1))
    return np.clip(out, 0, 255).astype(np.uint8)


def doc_cleanup(bgr: np.ndarray) -> np.ndarray:
    """Even out uneven background (shadows, yellowing) by dividing by an estimated background.
    Ink, stamps, and signatures are kept because only the slowly-varying illumination is removed."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    k = max(31, (min(gray.shape) // 20) | 1)
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    bg = cv2.GaussianBlur(bg, (0, 0), k / 3)
    bg = np.maximum(bg, 1).astype(np.float32)
    out = np.empty_like(bgr, dtype=np.float32)
    for c in range(3):
        out[..., c] = np.clip(bgr[..., c].astype(np.float32) / bg * 245.0, 0, 255)
    return out.astype(np.uint8)


def estimate_skew(bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    scale = 1000.0 / max(gray.shape)
    if scale < 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    best, best_score = 0.0, -1.0
    h, w = bw.shape
    for ang in np.arange(-5, 5.01, 0.25):
        M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
        r = cv2.warpAffine(bw, M, (w, h), flags=cv2.INTER_NEAREST)
        score = float(np.var(r.sum(axis=1)))
        if score > best_score:
            best, best_score = ang, score
    return best


def deskew(bgr: np.ndarray) -> tuple:
    ang = estimate_skew(bgr)
    if abs(ang) < 0.2:
        return bgr, 0.0
    h, w = bgr.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    out = cv2.warpAffine(bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return out, ang


def to_bw(bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    bs = max(31, (min(gray.shape) // 25) | 1)
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, bs, 15)
    return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)


def classical_upscale(bgr: np.ndarray, factor: int) -> np.ndarray:
    if factor <= 1:
        return bgr
    h, w = bgr.shape[:2]
    return cv2.resize(bgr, (w * factor, h * factor), interpolation=cv2.INTER_LANCZOS4)


# ---------------------------------------------------------------- AI (ONNX)
_session = None
_session_key = None


def _providers(device: str) -> list:
    import onnxruntime as ort
    avail = ort.get_available_providers()
    if device == "cpu":
        return ["CPUExecutionProvider"]
    prefs = [p for p in ("CUDAExecutionProvider", "DmlExecutionProvider") if p in avail]
    if device == "gpu" and not prefs:
        return ["CPUExecutionProvider"]
    return prefs + ["CPUExecutionProvider"]


def get_session(device: str = "auto"):
    global _session, _session_key
    if _session is not None and _session_key == device:
        return _session
    if not ai_model_available():
        raise FileNotFoundError(
            f"AI model not found: {model_path()}. See README 'AI model installation'. "
            "Classical upscaling will be used instead.")
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    try:
        _session = ort.InferenceSession(model_path(), so, providers=_providers(device))
    except Exception as e:
        raise RuntimeError(f"AI model could not be loaded: {e}") from e
    _session_key = device
    return _session


def ai_upscale_x4(bgr: np.ndarray, tile: int, device: str, progress=None, cancel=None) -> np.ndarray:
    """Tiled 4x inference with overlap to avoid seams; memory use is bounded by the tile size."""
    sess = get_session(device)
    inp = sess.get_inputs()[0].name
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    pad = 16
    S = 4
    out = np.zeros((h * S, w * S, 3), dtype=np.uint8)
    ys = list(range(0, h, tile))
    xs = list(range(0, w, tile))
    total = len(ys) * len(xs)
    n = 0
    for y0 in ys:
        for x0 in xs:
            if cancel and cancel():
                raise Cancelled()
            y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
            ya, xa = max(y0 - pad, 0), max(x0 - pad, 0)
            yb, xb = min(y1 + pad, h), min(x1 + pad, w)
            patch = rgb[ya:yb, xa:xb].astype(np.float32) / 255.0
            t = np.transpose(patch, (2, 0, 1))[None]
            res = sess.run(None, {inp: t})[0][0]
            res = np.clip(np.transpose(res, (1, 2, 0)) * 255.0 + 0.5, 0, 255).astype(np.uint8)
            oy0, ox0 = (y0 - ya) * S, (x0 - xa) * S
            out[y0 * S:y1 * S, x0 * S:x1 * S] = res[oy0:oy0 + (y1 - y0) * S, ox0:ox0 + (x1 - x0) * S]
            n += 1
            if progress:
                progress(n, total, f"AI upscaling tile {n}/{total}")
    return cv2.cvtColor(out, cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------- pipeline
def enhance_image(
    im: Image.Image,
    s: EnhanceSettings,
    progress: Optional[Callable[[int, int, str], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
    icc: Optional[bytes] = None,
) -> EnhanceResult:
    res = EnhanceResult(image=im, original_size=im.size, output_size=im.size, icc_profile=icc)
    bgr = _to_bgr(im)
    is_gray = im.mode == "L"

    def chk():
        if cancel and cancel():
            raise Cancelled()

    steps = []
    if s.jpeg_repair > 0: steps.append("jpeg")
    if s.denoise > 0: steps.append("denoise")
    if s.doc_cleanup: steps.append("doc")
    if s.deskew: steps.append("deskew")
    if s.white_balance or s.brightness or s.contrast: steps.append("color")
    if s.scale > 1: steps.append("upscale")
    if s.sharpen > 0: steps.append("sharpen")
    if s.bw_mode: steps.append("bw")
    total = max(len(steps), 1)
    done = 0

    def tick(msg):
        nonlocal done
        done += 1
        if progress:
            progress(done, total, msg)

    if s.jpeg_repair > 0:
        chk(); bgr = jpeg_repair(bgr, s.jpeg_repair)
        res.operations.append(f"JPEG artifact repair ({s.jpeg_repair:.2f})"); tick("JPEG repair")
    if s.denoise > 0:
        chk(); bgr = denoise(bgr, s.denoise, cancel)
        res.operations.append(f"Noise reduction ({s.denoise:.2f})"); tick("Noise reduction")
    if s.doc_cleanup:
        chk(); bgr = doc_cleanup(bgr)
        res.operations.append("Background cleanup (ink/stamps preserved)"); tick("Background cleanup")
    if s.deskew:
        chk(); bgr, ang = deskew(bgr)
        res.operations.append(f"Deskew ({ang:+.2f}°)" if ang else "Deskew (no skew detected)"); tick("Deskew")
    if s.white_balance or s.brightness or s.contrast:
        chk(); bgr = color_adjust(bgr, s.brightness, s.contrast, s.white_balance)
        res.operations.append("Colour/contrast adjustment"); tick("Colour adjustment")
    if s.scale > 1:
        chk()
        want_ai = s.use_ai_upscale and not s.document_safe
        if s.use_ai_upscale and s.document_safe:
            res.warnings.append("Document-safe mode: AI upscaling disabled; classical upscaling used.")
        if want_ai:
            try:
                x4 = ai_upscale_x4(bgr, s.tile, s.device,
                                   lambda a, b, m: progress and progress(done, total, m), cancel)
                if s.scale == 2:
                    h, w = bgr.shape[:2]
                    bgr = cv2.resize(x4, (w * 2, h * 2), interpolation=cv2.INTER_AREA)
                else:
                    bgr = x4
                res.ai_used = True
                res.operations.append(f"AI upscaling {s.scale}x (local ONNX model)")
                res.warnings.append("AI-generated detail may differ from the original. Verify important content.")
            except Cancelled:
                raise
            except Exception as e:
                res.warnings.append(f"AI model unavailable ({e}). Classical Lanczos upscaling used instead.")
                bgr = classical_upscale(bgr, s.scale)
                res.operations.append(f"Classical (Lanczos) upscaling {s.scale}x")
        else:
            bgr = classical_upscale(bgr, s.scale)
            res.operations.append(f"Classical (Lanczos) upscaling {s.scale}x")
        res.scale = s.scale
        tick("Upscaling")
    if s.sharpen > 0:
        chk(); bgr = sharpen(bgr, s.sharpen)
        res.operations.append(f"Edge-aware sharpening ({s.sharpen:.2f}, halo-limited)"); tick("Sharpening")
    if s.bw_mode:
        chk(); bgr = to_bw(bgr)
        res.operations.append("Black & white document mode"); tick("Black & white")

    out = _to_pil(bgr)
    if is_gray and not s.bw_mode:
        out = out.convert("L")
    res.image = out
    res.output_size = out.size
    return res


def save_image(res: EnhanceResult, path: str, fmt: str = "PNG", jpeg_quality: int = 95, keep_icc: bool = True) -> str:
    kw = {}
    if keep_icc and res.icc_profile:
        kw["icc_profile"] = res.icc_profile
    fmt = fmt.upper()
    if fmt in ("JPG", "JPEG"):
        res.image.convert("RGB").save(path, "JPEG", quality=jpeg_quality, subsampling=0, optimize=True, **kw)
    else:
        res.image.save(path, "PNG", compress_level=6, **kw)
    return path
