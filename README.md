Convenient tool for CooL stuff. Will be updated once i find stuff to add.

## Tools

- YouTube / Twitter video downloader (MP4)
- Audio (MP3) downloader
- Word (.docx) to PDF converter
- Image converter / resizer (PNG, JPG, WEBP, BMP)
- PDF merger (drag to reorder)

## Download

Grab `VeryUsefulTool.exe` from the [Releases](../../releases) page. No install needed, ffmpeg is bundled.
Windows may show a SmartScreen warning because the exe is unsigned: click "More info" then "Run anyway".

## Run from source

```
pip install -r requirements.txt
python main.py
```

## Build the exe

Pushing to `main` builds it on GitHub Actions (artifact). Pushing a `v*` tag also attaches it to a release.
Locally on Windows: `pip install -r requirements.txt pyinstaller` then `pyinstaller --noconfirm VeryUsefulTool.spec`.
