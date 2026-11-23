# PyInstaller spec: single-file, no-console Windows exe.
# Build with:  pyinstaller --noconfirm VeryUsefulTool.spec
import os
from PyInstaller.utils.hooks import collect_data_files

# Qt pieces the app never uses; dropping them keeps the exe small
DROP_FILES = {
    'opengl32sw.dll',      # ~20 MB software OpenGL fallback
    'qt6pdf.dll', 'qpdf.dll',
    'qt6network.dll',
}


def keep(entry):
    dest = entry[0].replace('\\', '/').lower()
    return os.path.basename(dest) not in DROP_FILES and '/translations/' not in dest


a = Analysis(
    ['main.py'],
    # bundled ffmpeg for video merging and MP3 conversion
    datas=collect_data_files('imageio_ffmpeg', subdir='binaries'),
    excludes=['tkinter', 'unittest', 'pydoc', 'test', 'PyQt6.QtNetwork', 'PyQt6.QtQml', 'PyQt6.QtQuick'],
)
a.binaries = [b for b in a.binaries if keep(b)]
a.datas = [d for d in a.datas if keep(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='VeryUsefulTool',
    console=False,
    upx=False,
)
