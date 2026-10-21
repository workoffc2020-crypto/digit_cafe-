import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.core import enhance as E
from app.core.enhance import EnhanceSettings, PRESETS, enhance_image, Cancelled


def _doc(size=(800, 1000)):
    im = Image.new("RGB", size, (235, 232, 220))
    d = ImageDraw.Draw(im)
    for y in range(60, size[1] - 60, 30):
        d.text((50, y), "Certificate No 123456 Name ABC", fill=(20, 20, 20))
    d.ellipse((600, 100, 740, 240), outline=(180, 0, 0), width=4)  # stamp
    return im


def test_all_presets_run():
    im = _doc((400, 500))
    for name, s in PRESETS.items():
        r = enhance_image(im, s)
        assert r.image.size[0] >= 400, name


def test_original_preset_is_identity():
    im = _doc((300, 300))
    r = enhance_image(im, PRESETS["Original (no enhancement)"])
    assert np.array_equal(np.asarray(im), np.asarray(r.image))
    assert r.operations == []


@pytest.mark.parametrize("scale", [2, 4])
def test_classical_upscale_dimensions(scale):
    im = _doc((200, 150))
    r = enhance_image(im, EnhanceSettings(scale=scale))
    assert r.output_size == (200 * scale, 150 * scale)
    assert not r.ai_used


def test_ai_requested_without_model_falls_back_with_warning(monkeypatch):
    monkeypatch.setattr(E, "ai_model_available", lambda: False)
    im = _doc((120, 120))
    r = enhance_image(im, EnhanceSettings(scale=2, use_ai_upscale=True))
    assert r.output_size == (240, 240)
    assert not r.ai_used
    assert any("AI model unavailable" in w for w in r.warnings)


def test_document_safe_blocks_ai():
    im = _doc((120, 120))
    r = enhance_image(im, EnhanceSettings(scale=2, use_ai_upscale=True, document_safe=True))
    assert not r.ai_used
    assert any("Document-safe" in w for w in r.warnings)


def test_doc_cleanup_keeps_ink_and_stamp():
    im = _doc((400, 500))
    r = enhance_image(im, PRESETS["Scanned Document Clarity"])
    a = np.asarray(r.image).astype(int)
    # dark text pixels still dark, background brighter, red stamp still red
    assert a[..., :].min() < 90
    assert a.mean() > np.asarray(im).astype(int).mean()


def test_deskew_detects_rotation():
    im = _doc((600, 800)).rotate(3, expand=False, fillcolor=(235, 232, 220))
    ang = E.estimate_skew(E._to_bgr(im))
    assert abs(abs(ang) - 3) <= 1.0


def test_cancel():
    im = _doc((300, 300))
    with pytest.raises(Cancelled):
        enhance_image(im, EnhanceSettings(denoise=0.5, sharpen=0.5), cancel=lambda: True)


def test_grayscale_and_save(tmp_path):
    im = Image.new("L", (100, 100), 128)
    r = enhance_image(im, EnhanceSettings(sharpen=0.5))
    p = E.save_image(r, str(tmp_path / "o.png"))
    assert Image.open(p).size == (100, 100)


def test_onnx_tiling_with_fake_model(tmp_path, monkeypatch):
    """Builds a tiny 4x nearest-neighbour ONNX model to prove tiling + CPU inference path works end to end."""
    onnx = pytest.importorskip("onnx")
    from onnx import helper, TensorProto
    inp = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, "h", "w"])
    out = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, "H", "W"])
    scales = helper.make_tensor("scales", TensorProto.FLOAT, [4], [1, 1, 4, 4])
    roi = helper.make_tensor("roi", TensorProto.FLOAT, [0], [])
    node = helper.make_node("Resize", ["input", "roi", "scales"], ["output"], mode="nearest")
    g = helper.make_graph([node], "g", [inp], [out], initializer=[scales, roi])
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 13)])
    m.ir_version = 8
    path = tmp_path / E.MODEL_FILENAME
    onnx.save(m, str(path))
    monkeypatch.setattr(E, "model_path", lambda: str(path))
    monkeypatch.setattr(E, "_session", None)
    im = Image.fromarray((np.random.default_rng(0).random((70, 90, 3)) * 255).astype("uint8"))
    for scale in (2, 4):
        r = enhance_image(im, EnhanceSettings(scale=scale, use_ai_upscale=True, tile=32, device="cpu"))
        assert r.ai_used and r.output_size == (90 * scale, 70 * scale)
    # 4x nearest => tiles must reassemble exactly
    r4 = enhance_image(im, EnhanceSettings(scale=4, use_ai_upscale=True, tile=32, device="cpu"))
    ref = np.asarray(im).repeat(4, 0).repeat(4, 1)
    assert np.abs(np.asarray(r4.image).astype(int) - ref.astype(int)).max() <= 1
