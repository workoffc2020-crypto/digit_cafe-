# Cyber Cafe Studio — Install Guide (Hindi / Hinglish, step by step)

Aapke PC par error aaya: **"py is not recognized"**. Iska matlab hai **Python install nahi hai** (ya PATH mein add nahi hua).
Neeche ke steps follow karein.

---

## PART 1 — Python install karein (sirf ek baar)

1. Browser mein kholein: **https://www.python.org/downloads/windows/**
2. **"Python 3.12.x"** dhoondhein → **"Windows installer (64-bit)"** download karein.
   (Python 3.14 / 3.15 mat lena — naye versions par kuch libraries nahi chalti.)
3. Downloaded file ko double-click karein.
4. **SABSE ZAROORI:** pehli screen par neeche **"Add python.exe to PATH"** ka box **tick ✔ karein**.
5. **"Install Now"** dabayein. Khatam hone par **Close**.
6. **Test:** Start menu mein `cmd` likhein → Enter → likhein `py --version` → Enter.
   `Python 3.12.x` dikhna chahiye. Agar nahi dikha to PC **restart** karke phir try karein.

## PART 2 — Project folder taiyaar karein

1. `CyberCafeStudio.zip` par **Right-click → Extract All…** (zip ke andar se mat chalana!).
2. Folder aise kisi simple jagah rakhein: `C:\CyberCafeStudio` (naam mein Hindi/space na ho to behtar).

## PART 3A — SABSE AASAAN: app seedha chalayein (installer ke bina)

1. Folder kholein → **`run_app.bat`** par double-click. Ek black window khulegi aur khuli rahegi (band nahi hogi) — wahin progress dikhega.
2. Pehli baar internet chahiye; libraries install hongi (5–15 minute). Black window band mat karna.
3. Uske baad **Cyber Cafe Studio** khul jayega. Agli baar se `run_app.bat` turant chalega.

## PART 3B — Setup.exe (installer) banana

1. **Inno Setup 6** install karein: **https://jrsoftware.org/isdl.php** → "Inno Setup 6.x" download → Next, Next, Install.
2. Folder mein **`build_windows.bat`** par double-click.
3. Black window mein steps chalenge (Python dhoondhna → libraries → icon → tests → build → Setup). **15–30 minute** lag sakte hain, wait karein.
4. Aakhir mein likha aayega **DONE!** aur file milegi:
   **`dist_installer\CyberCafeStudio_Setup.exe`**
5. Is `CyberCafeStudio_Setup.exe` par double-click → **Next → Install → Finish**.
   Desktop par **Cyber Cafe Studio** ka icon aa jayega.
6. Is Setup.exe ko pen-drive se dusre PC par bhi install kar sakte hain (wahan Python ki zaroorat nahi).

## Agar koi error aaye

| Error | Kya karein |
|---|---|
| `Python NAHI MILA` | Part 1 dobara karein, **PATH wala box tick** karna na bhoolein, phir PC restart. |
| `pip ... could not find a version` | Python 3.14 laga hoga → Python 3.12 install karein, `.venv` folder delete karke phir chalayein. |
| Internet / timeout error | Internet check karein aur `.bat` phir se chalayein (wahin se aage badhega). |
| `BUILD FAILED` | Window mein neeche ki 10–15 lines copy/screenshot karke mujhe bhejein. |
| Windows "SmartScreen" warning | **More info → Run anyway** (app unsigned hai, isliye aata hai). |

## Use kaise karein (short)
- **Convert Without Quality Loss** → certificates, forms, ID, legal papers (original quality, AI nahi).
- **Enhance with AI + Convert to PDF** → photos / kharab scans ko behtar karke PDF.
- Files drag-drop karein, thumbnails ko drag karke order badlein, PDF ka naam/jagah chunein.
- AI model optional hai (README dekhein). Bina model ke bhi app poori tarah chalta hai.

## NAYA: PDF Tools (PDF → Image / Word / Excel)
- Left menu mein **PDF Tools** kholein → upar se **PDF → Image**, **PDF → Word** ya **PDF → Excel** chunein.
- PDF drag-drop karein → **Convert** dabayein. Nayi files PDF ke paas **Converted** folder mein banti hain (purani file kabhi overwrite nahi hoti).
- **Purani install wale dhyan dein:** naya folder purane ke upar extract karein aur `run_app.bat` chalayein. Pehli baar naye libraries
  install honge (internet chahiye, 10-15 minute). Uske baad sab offline chalega.
- **Scanned PDF** ko offline OCR se padha jata hai — **English aur numbers achhe se**, **Hindi abhi support nahi hai**.
  Peela highlight = OCR ko shak hai, check kar lein.
- Word mein layout lagbhag same aata hai, par bilkul 100% same nahi hota. Excel mein phone/Aadhaar/0123 jaisi values jaan-bujhkar text rehti hain.
- `build_windows.bat` se pehle C: drive par kam se kam **20-25 GB khali** rakhein (pichli baar system hang isi wajah se hua tha).
