"""Each enhancement slider must have a real, measurable, monotonic effect."""
import cv2
import numpy as np
from PIL import Image

from app.core import enhance as E
from app.core.enhance import EnhanceSettings, enhance_image


def _clean(w=320, h=240):
    img = np.zeros((h, w, 3), np.float32)
    img[..., 0] = np.linspace(60, 200, w)[None, :]
    img[..., 1] = np.linspace(90, 160, h)[:, None]
    img[..., 2] = 110
    img[60:180, 80:240] = (200, 60, 60)           # sharp rectangle
    img = np.clip(img, 0, 255).astype(np.uint8)
    cv2.putText(img, "Hello 123", (90, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
    return img


def _mse(a, b):
    return float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))


def _lapvar(a):
    return float(cv2.Laplacian(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())


def test_noise_reduction_slider():
    clean = _clean()
    noisy = np.clip(clean.astype(np.float32) + np.random.default_rng(0).normal(0, 14, clean.shape), 0, 255).astype(np.uint8)
    errs = [_mse(E.denoise(noisy, s), clean) for s in (0.0, 0.3, 0.6, 1.0)]
    assert errs[1] < errs[0] * 0.75
    assert errs[2] < errs[1]
    assert errs[3] < errs[0] * 0.4


def test_noise_reduction_large_strips_match_shape():
    big = np.random.default_rng(1).integers(0, 255, (1800, 2000, 3), dtype=np.uint8)
    out = E.denoise(big, 0.3)
    assert out.shape == big.shape and out.dtype == np.uint8


def test_sharpen_slider_increases_detail_without_big_halos():
    clean = _clean()
    soft = cv2.GaussianBlur(clean, (0, 0), 1.6)
    v = [_lapvar(E.sharpen(soft, s)) for s in (0.0, 0.3, 0.6, 1.0)]
    assert v[1] > v[0] * 1.3 and v[2] > v[1] and v[3] > v[2]
    out = E.sharpen(soft, 1.0).astype(int)
    assert out.min() >= int(soft.min()) - 45 and out.max() <= int(soft.max()) + 45     # bounded overshoot
    flat = np.full((100, 100, 3), 128, np.uint8)
    assert np.array_equal(E.sharpen(flat, 1.0), flat)                       # nothing invented in flat areas


def test_jpeg_repair_slider_reduces_blockiness():
    clean = _clean()
    ok, buf = cv2.imencode(".jpg", clean, [cv2.IMWRITE_JPEG_QUALITY, 8])
    bad = cv2.imdecode(buf, cv2.IMREAD_COLOR)

    def blockiness(a):
        g = cv2.cvtColor(a, cv2.COLOR_BGR2YCrCb)[..., 1:].astype(np.float32)  # chroma shows blocks most
        dx = np.abs(np.diff(g, axis=1)).mean(axis=(0, 2))
        edge = dx[7::8].mean()
        other = np.delete(dx, np.arange(7, len(dx), 8)).mean()
        return edge - other

    b0 = blockiness(bad)
    errs = [_mse(E.jpeg_repair(bad, s), clean) for s in (0.0, 0.5, 1.0)]
    assert blockiness(E.jpeg_repair(bad, 0.8)) < b0
    assert errs[1] < errs[0]


def test_brightness_and_contrast_sliders():
    clean = _clean()
    m = [E.color_adjust(clean, b, 0, False).mean() for b in (-0.5, 0.0, 0.5)]
    assert m[0] < m[1] - 20 and m[2] > m[1] + 20
    sd = [E.color_adjust(clean, 0, c, False).std() for c in (-0.5, 0.0, 0.5)]
    assert sd[0] < sd[1] < sd[2]
    for b in (-1, 1):
        o = E.color_adjust(clean, b, 1, True)
        assert o.dtype == np.uint8 and 0 <= o.min() and o.max() <= 255


def test_sliders_through_full_pipeline_and_zero_is_identity():
    clean = _clean()
    im = Image.fromarray(cv2.cvtColor(clean, cv2.COLOR_BGR2RGB))
    base = np.asarray(enhance_image(im, EnhanceSettings(sharpen=0.0)).image)
    assert np.array_equal(base, np.asarray(im))
    for kw in ({"denoise": 0.5}, {"jpeg_repair": 0.5}, {"sharpen": 0.5}, {"brightness": 0.4}, {"contrast": 0.4}):
        out = np.asarray(enhance_image(im, EnhanceSettings(**kw)).image)
        assert not np.array_equal(out, np.asarray(im)), kw
