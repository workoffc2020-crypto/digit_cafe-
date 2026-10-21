# Cyber Cafe Studio

Offline Windows desktop app for cyber cafes: **original-quality Image → PDF** and **optional AI image enhancement**.
Two independent buttons:

| Button | What it does |
|---|---|
| **Convert Without Quality Loss** | Original-quality path. JPEGs are embedded byte-for-byte (no re-encode), PNGs stay lossless, nothing is resampled. AI is never involved. |
| **Enhance with AI + Convert to PDF** | Enhances each image (a copy – originals are never touched), then builds the PDF from the enhanced pixels. |

Everything runs on your PC. No uploads, no telemetry, no network access.

---

## 1. Getting the installer (`.exe`) — Windows

> **Beginner?** Read **`INSTALL_GUIDE_HINDI.md`** (step-by-step, Hindi/Hinglish). To just run the app without an installer, double-click **`run_app.bat`**.

The installer must be built **on Windows** (a Windows `.exe` cannot be produced on Linux/macOS). Choose one:

**A. One-click on your PC**
1. Install **Python 3.12** from python.org (tick *Add python.exe to PATH*).
2. Install **Inno Setup 6** from jrsoftware.org (needed only to create the installer).
3. Double-click **`build_windows.bat`**.
   It installs dependencies, generates the icon, runs all tests, builds the app, **tests the packaged .exe**
   (`CyberCafeStudio.exe --selftest`) and creates `dist_installer\CyberCafeStudio_Setup.exe`.

**B. Automatic with GitHub** – push this folder to a GitHub repo, open *Actions → Build Windows installer → Run workflow*,
then download the `CyberCafeStudio_Setup` artifact.

Without Inno Setup you still get a portable app: `dist\CyberCafeStudio\CyberCafeStudio.exe`.

### Install & icon
Run `CyberCafeStudio_Setup.exe`. It installs to *Program Files*, creates a Start-menu entry and optional desktop shortcut,
and a *Send to → Cyber Cafe Studio* entry (select images in Explorer → right-click → Send to → opens them in the app).
The app's own icon (document + picture + AI sparkle, `assets/app.ico`, 16–256 px) is used for the .exe, the installer,
shortcuts, the window title bar and the taskbar. Replace `assets/app.ico` with your own to rebrand.

---

## 2. Using the app
1. **Dashboard** → pick a tool (Image to PDF, AI Image Enhancer, AI Upscaler, Document Clarity, Batch, Recent).
2. **Workspace**: drag & drop images or use *Add files / Add folder*. Drag thumbnails to reorder pages.
3. **PDF Settings**: A4/A3/A5/Letter/Legal/Custom/Original size, orientation, margin, fit or fill, DPI.
4. **AI Enhancement**: choose a preset or tune sliders → *Preview Enhancement* → drag the divider to compare;
   zoom with wheel, **Fit / 100% / 200%**; *Save Enhanced Image…* saves a new file.
**PDF Tools page:** choose *PDF → Image* (PNG/JPG/TIFF, or extract the original photos untouched), *PDF → Word* (.docx) or
*PDF → Excel* (.xlsx). Add PDFs (drag & drop), optional page range / password, press **Convert**. Output goes to a `Converted`
folder next to the PDF; existing files are never overwritten.

5. Click **Convert Without Quality Loss** *or* **Enhance with AI + Convert to PDF**.
6. A **Quality Verification Report** opens: sizes, embedded format, bit-identical JPEG check, pixel check, PSNR, notes.
   Status badges (Original Data Preservation Mode, Lossless Output Format, Lossy Conversion Detected,
   AI Enhancement Applied, Quality Verification Complete) are shown **only if verified from the finished PDF**.

**Which button for what**
- Certificates, forms, ID cards, legal papers → **Convert Without Quality Loss**. If a scan is faint, use *Scanned Document Clarity*
  or *Small Text Readability* (faithful classical processing, generative AI is blocked on these).
- Photos → *Natural Photo Enhancement*, *Old Photo Restoration*, *Maximum Detail Upscaling*.

### Presets
Original · Natural Photo · Maximum Detail Upscaling · Old Photo Restoration · Scanned Document Clarity ·
Small Text Readability · Screenshot and Graphics · Low-Quality JPEG Repair.

---

## 3. AI model installation (optional, offline)
The app works without it (classical Lanczos upscaling + sharpening is used and clearly reported).
For AI 2×/4× upscaling, install a Real-ESRGAN-style **x4 ONNX** model (input NCHW float32 RGB 0–1, output 4×):

```
python tools\install_model.py C:\path\to\realesrgan_x4.onnx
```
(or `--url <link> --sha256 <hash>` — the download happens only when you run this command). The model is copied to
`models\realesrgan_x4.onnx`; the installer packages the `models` folder if it exists at build time.
No model file is bundled in this project: obtain one yourself and check its licence (Real-ESRGAN code is BSD-3-Clause;
check the licence of the specific weights you download). See `THIRD_PARTY_LICENSES.md`.

GPU: install `onnxruntime-directml` instead of `onnxruntime` (works on NVIDIA/AMD/Intel GPUs on Windows 10/11),
or `onnxruntime-gpu` (NVIDIA + CUDA). Pick *Advanced → AI device*. CPU-only works everywhere.

---

## 4. Hardware
| | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 64-bit | Windows 11 |
| CPU | 4 cores | 6+ cores |
| RAM | 4 GB (PDF conversion), 8 GB (2× enhance) | 16 GB (4× on large photos) |
| GPU | not required | any DirectX 12 GPU with onnxruntime-directml |
| Disk | 600 MB | 2 GB (with model) |

The app estimates memory before enhancement and warns if the job may not fit; lower the upscale factor or tile size.

---

## 5. Privacy
Offline operation, no telemetry, no network calls. Temporary files go to a private temp folder that is deleted after each job.
Logs (`%LOCALAPPDATA%\CyberCafeStudio\logs\app.log`) contain errors only, never image content.

## 6. Tests
`python -m pytest tests -q` – covers JPEG bit-identical embedding, PNG pixel identity, EXIF rotation, transparent PNG,
very large (9000×9000) image, corrupted files, multi-image batches, cancel, 2×/4× upscaling (including a real ONNX tiling test
on CPU), presets, document-safe mode, truthful status reporting, and GUI smoke tests.
`CyberCafeStudio.exe --selftest` re-checks the core engines inside the packaged build.

## 7. Known limitations (honest list)
- The Windows installer was **not built or run on Windows in the authoring environment**; `build_windows.bat` / the GitHub workflow
  build it and run the packaged self-test for you. Please test the final installer on your PC before daily use.
- No AI model is bundled; AI quality depends on the model you install. AI output can differ from the original.
- Cropping: *Fill page* crops edges at the page boundary (pixels unchanged). There is no interactive crop-rectangle tool yet.
- Mirrored EXIF orientations (rare) are not applied to JPEGs that are embedded losslessly (reported in the notes).
- CMYK JPEGs are embedded as-is; some PDF viewers display CMYK differently.
- Transparent PNGs must be flattened onto white for PDF; this is reported as a transparency change.
- Enhanced images embedded as PNG can make large PDFs; choose *JPEG* in Advanced for smaller files (reported as lossy).
- Deskew corrects small angles (±5°) only.
- **PDF Tools** (PDF → Image / Word / Excel): scanned PDFs are read with offline OCR that works well for **English letters and digits only**;
  Hindi/other scripts are not supported. Uncertain OCR text is highlighted yellow in Word. Word output keeps layout/tables for text PDFs
  but is never pixel-identical to the PDF. Excel: dates stay as text; IDs, phone/Aadhaar numbers and leading-zero values stay text on purpose.
  PyMuPDF (AGPL) / pdf2docx (GPL): see THIRD_PARTY_LICENSES.md before redistributing.
