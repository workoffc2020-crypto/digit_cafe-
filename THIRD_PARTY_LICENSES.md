# Third-party components

| Component | Purpose | Licence (verify current terms before redistribution) |
|---|---|---|
| PySide6 / Qt for Python | GUI | LGPL-3.0 (dynamic linking, as packaged by PyInstaller) |
| Pillow | image I/O | HPND |
| OpenCV (opencv-python-headless) | image processing | Apache-2.0 |
| NumPy | arrays | BSD-3-Clause |
| img2pdf | lossless PDF embedding | LGPL-3.0 |
| pikepdf (qpdf) | PDF inspection | MPL-2.0 (qpdf: Apache-2.0) |
| ONNX Runtime | local AI inference | MIT |
| Real-ESRGAN (optional model, NOT bundled) | super-resolution | code BSD-3-Clause; check the licence of the weights you download |
| PyMuPDF | PDF render / text / tables | **AGPL-3.0** (or Artifex commercial licence) |
| pdf2docx | PDF → Word | **GPL-3.0** |
| python-docx / openpyxl | write Word / Excel | MIT / MIT |
| RapidOCR (onnxruntime) + bundled models | offline OCR for scanned PDFs | Apache-2.0 (English/digits good; Hindi not supported) |
| PyInstaller / Inno Setup | build tools | GPL with bootloader exception / Inno Setup licence |

Because PySide6 and img2pdf are LGPL, keep them as separate libraries (the default PyInstaller one-folder build does this)
and retain this notice when redistributing.

**PDF Tools licensing note:** PyMuPDF (AGPL) and pdf2docx (GPL) are fine for using the app privately in your own cafe.
If you ever give or sell the installer to others you must follow those licences (offer source) or buy an Artifex licence for PyMuPDF.
