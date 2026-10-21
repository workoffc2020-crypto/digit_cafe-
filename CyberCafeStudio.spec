# PyInstaller spec — run:  pyinstaller CyberCafeStudio.spec --noconfirm
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [("assets/app.ico", "assets"), ("assets/app.png", "assets"), ("assets/check.png", "assets")]
binaries, hiddenimports = [], ["app", "app.core", "app.ui"]
for pkg in ("onnxruntime", "pikepdf", "img2pdf", "pymupdf", "pdf2docx", "docx", "openpyxl", "rapidocr_onnxruntime"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h
hiddenimports += collect_submodules("app") + ["pyclipper", "shapely", "yaml", "six", "fitz"]

a = Analysis(["main.py"], pathex=["."], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             excludes=["tkinter", "matplotlib", "torch", "scipy", "pytest", "onnx"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="CyberCafeStudio", console=False,
          icon="assets/app.ico", version="installer/version_info.txt", upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="CyberCafeStudio", upx=False)
