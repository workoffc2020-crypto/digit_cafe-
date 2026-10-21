"""Install a Real-ESRGAN x4 ONNX model for offline AI upscaling.

Usage:
  python tools/install_model.py path\to\model.onnx
  python tools/install_model.py --url https://.../model.onnx [--sha256 <hash>]

The model must take NCHW float32 RGB input in [0,1] and return a 4x upscaled image.
The file is copied to models\realesrgan_x4.onnx. Downloads happen only when YOU run this with --url.
"""
import argparse, hashlib, os, shutil, sys, urllib.request

DEST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "realesrgan_x4.onnx")

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

ap = argparse.ArgumentParser()
ap.add_argument("file", nargs="?")
ap.add_argument("--url")
ap.add_argument("--sha256")
a = ap.parse_args()
os.makedirs(os.path.dirname(DEST), exist_ok=True)
tmp = DEST + ".part"
if a.url:
    print("Downloading", a.url); urllib.request.urlretrieve(a.url, tmp)
elif a.file:
    shutil.copyfile(a.file, tmp)
else:
    ap.error("give a file path or --url")
if a.sha256 and sha256(tmp).lower() != a.sha256.lower():
    os.remove(tmp); sys.exit("Checksum mismatch - model rejected.")
import onnxruntime as ort
try:
    s = ort.InferenceSession(tmp, providers=["CPUExecutionProvider"])
    print("Model loads OK. Input:", s.get_inputs()[0].shape)
except Exception as e:
    os.remove(tmp); sys.exit(f"Model could not be loaded: {e}")
os.replace(tmp, DEST)
print("Installed ->", DEST, "\nSHA256:", sha256(DEST))
