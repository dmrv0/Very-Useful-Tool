from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter


def convert_image(src_path, dst_path, max_width=0, quality=90):
    img = QImage(src_path)
    if img.isNull():
        raise ValueError(f"Could not read image: {src_path}")

    if max_width and img.width() > max_width:
        img = img.scaledToWidth(max_width, Qt.TransformationMode.SmoothTransformation)

    # JPG has no transparency; flatten onto white instead of the default black
    if dst_path.lower().endswith(('.jpg', '.jpeg')) and img.hasAlphaChannel():
        flat = QImage(img.size(), QImage.Format.Format_RGB32)
        flat.fill(Qt.GlobalColor.white)
        painter = QPainter(flat)
        painter.drawImage(0, 0, img)
        painter.end()
        img = flat

    if not img.save(dst_path, quality=quality):
        raise ValueError(f"Could not write image: {dst_path}")
