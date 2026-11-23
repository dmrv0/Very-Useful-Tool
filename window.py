import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QHBoxLayout, QStackedWidget, QMessageBox,
    QProgressBar, QListWidget, QAbstractItemView, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont

from downloader import DownloadWorker
from image_utils import convert_image
from pdf_utils import convert_docx_to_pdf, merge_pdfs


IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tif', '.tiff')

INPUT_STYLE = (
    "padding: 6px; border: 1px solid #555; border-radius: 4px;"
    "background-color: #333; color: white;"
)


BTN_STYLE = """
    QPushButton {
        padding: 15px;
        background-color: #333;
        border: 2px solid #555;
        border-radius: 8px;
        font-size: 16px;
        font-weight: bold;
        color: white;
    }
    QPushButton:hover {
        background-color: #444;
        border: 2px solid #008CBA;
    }
"""

PROGRESS_STYLE_BLUE = """
    QProgressBar {
        border: 1px solid #555;
        border-radius: 4px;
        background-color: #333;
        color: white;
        text-align: center;
    }
    QProgressBar::chunk { background-color: #008CBA; border-radius: 3px; }
"""

PROGRESS_STYLE_GREEN = """
    QProgressBar {
        border: 1px solid #555;
        border-radius: 4px;
        background-color: #333;
        color: white;
        text-align: center;
    }
    QProgressBar::chunk { background-color: #4CAF50; border-radius: 3px; }
"""


class DragDropLabel(QLabel):
    def __init__(self, title, extensions=('.docx',)):
        super().__init__(title)
        self.extensions = extensions
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 20px;
                background-color: #2b2b2b;
                color: #ccc;
            }
        """)
        self.setAcceptDrops(True)
        self.selected_files = []

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        self.add_files([u.toLocalFile() for u in event.mimeData().urls()])

    def add_files(self, files):
        valid = [f for f in files if f.lower().endswith(self.extensions)]
        self.selected_files.extend(valid)
        if self.selected_files:
            names = [os.path.basename(f) for f in self.selected_files]
            preview = ", ".join(names[:3]) + ("..." if len(names) > 3 else "")
            self.setText(f"Selected {len(self.selected_files)} files:\n{preview}")


class PdfDropList(QListWidget):
    """List of PDFs that accepts dropped files and can be reordered by dragging."""

    def __init__(self):
        super().__init__()
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 6px;
                background-color: #2b2b2b;
                color: #ccc;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            self.add_files([u.toLocalFile() for u in event.mimeData().urls()])
            event.accept()
        else:
            super().dropEvent(event)

    def add_files(self, files):
        for f in files:
            if f.lower().endswith('.pdf'):
                self.addItem(os.path.basename(f))
                self.item(self.count() - 1).setData(Qt.ItemDataRole.UserRole, f)

    def paths(self):
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Tool Application")
        self.resize(560, 680)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self._setup_main_menu()
        self._setup_video_downloader()
        self._setup_pdf_converter()
        self._setup_image_converter()
        self._setup_pdf_merger()

        self.download_worker = None
        self.audio_only = False
        self.video_save_path = ""
        self.pdf_dest_path = ""
        self.image_dest_path = ""

    # ------------------------------------------------------------------ pages

    def _setup_main_menu(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("Select a Tool")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        btn_yt = QPushButton("YouTube Video Downloader")
        btn_yt.setStyleSheet(BTN_STYLE)
        btn_yt.clicked.connect(lambda: self._open_downloader("YouTube"))

        btn_tw = QPushButton("Twitter Video Downloader")
        btn_tw.setStyleSheet(BTN_STYLE)
        btn_tw.clicked.connect(lambda: self._open_downloader("Twitter"))

        btn_mp3 = QPushButton("Audio (MP3) Downloader")
        btn_mp3.setStyleSheet(BTN_STYLE)
        btn_mp3.clicked.connect(lambda: self._open_downloader("Audio (MP3)", audio_only=True))

        btn_pdf = QPushButton("Word to PDF Converter")
        btn_pdf.setStyleSheet(BTN_STYLE)
        btn_pdf.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))

        btn_img = QPushButton("Image Converter / Resizer")
        btn_img.setStyleSheet(BTN_STYLE)
        btn_img.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))

        btn_merge = QPushButton("PDF Merger")
        btn_merge.setStyleSheet(BTN_STYLE)
        btn_merge.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(4))

        layout.addWidget(btn_yt)
        layout.addWidget(btn_tw)
        layout.addWidget(btn_mp3)
        layout.addWidget(btn_pdf)
        layout.addWidget(btn_img)
        layout.addWidget(btn_merge)

        self.stacked_widget.addWidget(page)

    def _setup_video_downloader(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        self.video_title_lbl = QLabel("Video Downloader")
        self.video_title_lbl.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(self.video_title_lbl)

        layout.addWidget(QLabel("Video URL:"))
        self.url_input = QLineEdit()
        self.url_input.setStyleSheet(
            "padding: 8px; border: 1px solid #555; border-radius: 4px;"
            "background-color: #333; color: white;"
        )
        layout.addWidget(self.url_input)

        # Save-as row
        save_row = QHBoxLayout()
        save_btn = QPushButton("Save As...")
        save_btn.setStyleSheet(
            "padding: 8px; background-color: #4CAF50; border: none;"
            "border-radius: 4px; color: white; font-weight: bold;"
        )
        save_btn.clicked.connect(self._pick_video_save_path)
        self.video_path_lbl = QLabel("No file selected")
        self.video_path_lbl.setStyleSheet("color: #aaa;")
        save_row.addWidget(save_btn)
        save_row.addWidget(self.video_path_lbl, stretch=1)
        layout.addLayout(save_row)

        # Progress bar + status
        self.video_progress = QProgressBar()
        self.video_progress.setRange(0, 100)
        self.video_progress.setValue(0)
        self.video_progress.setVisible(False)
        self.video_progress.setStyleSheet(PROGRESS_STYLE_BLUE)
        layout.addWidget(self.video_progress)

        self.video_status_lbl = QLabel("")
        self.video_status_lbl.setStyleSheet("color: #aaa; font-size: 12px;")
        self.video_status_lbl.setVisible(False)
        layout.addWidget(self.video_status_lbl)

        # Buttons
        self.download_btn = QPushButton("Download")
        self.download_btn.setStyleSheet(
            "padding: 12px; background-color: #008CBA; border-radius: 4px;"
            "font-weight: bold; font-size: 14px; color: white;"
        )
        self.download_btn.clicked.connect(self._start_download)
        layout.addWidget(self.download_btn)

        back_btn = QPushButton("Back to Menu")
        back_btn.setStyleSheet("padding: 10px; background-color: #555; border-radius: 4px; color: white;")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn)
        layout.addStretch()

        self.stacked_widget.addWidget(page)

    def _setup_pdf_converter(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        title = QLabel("Word to PDF Converter")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        layout.addWidget(QLabel("Select Word (.docx) Files:"))
        self.drop_zone = DragDropLabel("Drag and Drop .docx Files Here")
        layout.addWidget(self.drop_zone)

        browse_btn = QPushButton("Browse Files...")
        browse_btn.setStyleSheet(
            "padding: 8px; background-color: #555; border: none; border-radius: 4px; color: white;"
        )
        browse_btn.clicked.connect(self._browse_docx)
        layout.addWidget(browse_btn)

        dest_row = QHBoxLayout()
        dest_btn = QPushButton("Select Destination")
        dest_btn.setStyleSheet(
            "padding: 8px; background-color: #4CAF50; border: none;"
            "border-radius: 4px; color: white; font-weight: bold;"
        )
        dest_btn.clicked.connect(self._pick_pdf_dest)
        self.pdf_dest_lbl = QLabel("No destination selected")
        self.pdf_dest_lbl.setStyleSheet("color: #aaa;")
        dest_row.addWidget(dest_btn)
        dest_row.addWidget(self.pdf_dest_lbl, stretch=1)
        layout.addLayout(dest_row)

        self.pdf_progress = QProgressBar()
        self.pdf_progress.setRange(0, 100)
        self.pdf_progress.setValue(0)
        self.pdf_progress.setVisible(False)
        self.pdf_progress.setStyleSheet(PROGRESS_STYLE_GREEN)
        layout.addWidget(self.pdf_progress)

        self.convert_btn = QPushButton("Convert to PDF")
        self.convert_btn.setStyleSheet(
            "padding: 12px; background-color: #008CBA; border-radius: 4px;"
            "font-weight: bold; font-size: 14px; color: white;"
        )
        self.convert_btn.clicked.connect(self._convert_pdfs)
        layout.addWidget(self.convert_btn)

        back_btn = QPushButton("Back to Menu")
        back_btn.setStyleSheet("padding: 10px; background-color: #555; border-radius: 4px; color: white;")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn)

        self.stacked_widget.addWidget(page)

    def _setup_image_converter(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        title = QLabel("Image Converter / Resizer")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        layout.addWidget(QLabel("Select Images (PNG, JPG, WEBP, BMP, GIF, TIFF):"))
        self.image_drop_zone = DragDropLabel("Drag and Drop Images Here", IMAGE_EXTS)
        layout.addWidget(self.image_drop_zone)

        browse_btn = QPushButton("Browse Files...")
        browse_btn.setStyleSheet(
            "padding: 8px; background-color: #555; border: none; border-radius: 4px; color: white;"
        )
        browse_btn.clicked.connect(self._browse_images)
        layout.addWidget(browse_btn)

        options_row = QHBoxLayout()
        options_row.addWidget(QLabel("Format:"))
        self.image_format = QComboBox()
        self.image_format.addItems(["JPG", "PNG", "WEBP", "BMP"])
        self.image_format.setStyleSheet(INPUT_STYLE)
        options_row.addWidget(self.image_format)

        options_row.addWidget(QLabel("Max width:"))
        self.image_width = QSpinBox()
        self.image_width.setRange(0, 10000)
        self.image_width.setSingleStep(100)
        self.image_width.setSpecialValueText("Original")
        self.image_width.setStyleSheet(INPUT_STYLE)
        options_row.addWidget(self.image_width)

        options_row.addWidget(QLabel("Quality:"))
        self.image_quality = QSpinBox()
        self.image_quality.setRange(1, 100)
        self.image_quality.setValue(90)
        self.image_quality.setStyleSheet(INPUT_STYLE)
        options_row.addWidget(self.image_quality)
        layout.addLayout(options_row)

        dest_row = QHBoxLayout()
        dest_btn = QPushButton("Select Destination")
        dest_btn.setStyleSheet(
            "padding: 8px; background-color: #4CAF50; border: none;"
            "border-radius: 4px; color: white; font-weight: bold;"
        )
        dest_btn.clicked.connect(self._pick_image_dest)
        self.image_dest_lbl = QLabel("No destination selected")
        self.image_dest_lbl.setStyleSheet("color: #aaa;")
        dest_row.addWidget(dest_btn)
        dest_row.addWidget(self.image_dest_lbl, stretch=1)
        layout.addLayout(dest_row)

        self.image_progress = QProgressBar()
        self.image_progress.setRange(0, 100)
        self.image_progress.setVisible(False)
        self.image_progress.setStyleSheet(PROGRESS_STYLE_GREEN)
        layout.addWidget(self.image_progress)

        self.image_convert_btn = QPushButton("Convert Images")
        self.image_convert_btn.setStyleSheet(
            "padding: 12px; background-color: #008CBA; border-radius: 4px;"
            "font-weight: bold; font-size: 14px; color: white;"
        )
        self.image_convert_btn.clicked.connect(self._convert_images)
        layout.addWidget(self.image_convert_btn)

        back_btn = QPushButton("Back to Menu")
        back_btn.setStyleSheet("padding: 10px; background-color: #555; border-radius: 4px; color: white;")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn)

        self.stacked_widget.addWidget(page)

    def _setup_pdf_merger(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        title = QLabel("PDF Merger")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        layout.addWidget(QLabel("Drop PDFs here, then drag them to set the order:"))
        self.merge_list = PdfDropList()
        layout.addWidget(self.merge_list, stretch=1)

        list_row = QHBoxLayout()
        browse_btn = QPushButton("Add PDFs...")
        browse_btn.setStyleSheet(
            "padding: 8px; background-color: #555; border: none; border-radius: 4px; color: white;"
        )
        browse_btn.clicked.connect(self._browse_merge_pdfs)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setStyleSheet(
            "padding: 8px; background-color: #555; border: none; border-radius: 4px; color: white;"
        )
        remove_btn.clicked.connect(
            lambda: [self.merge_list.takeItem(self.merge_list.row(i)) for i in self.merge_list.selectedItems()]
        )
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(
            "padding: 8px; background-color: #555; border: none; border-radius: 4px; color: white;"
        )
        clear_btn.clicked.connect(self.merge_list.clear)
        list_row.addWidget(browse_btn)
        list_row.addWidget(remove_btn)
        list_row.addWidget(clear_btn)
        layout.addLayout(list_row)

        self.merge_btn = QPushButton("Merge PDFs")
        self.merge_btn.setStyleSheet(
            "padding: 12px; background-color: #008CBA; border-radius: 4px;"
            "font-weight: bold; font-size: 14px; color: white;"
        )
        self.merge_btn.clicked.connect(self._merge_pdfs)
        layout.addWidget(self.merge_btn)

        back_btn = QPushButton("Back to Menu")
        back_btn.setStyleSheet("padding: 10px; background-color: #555; border-radius: 4px; color: white;")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn)

        self.stacked_widget.addWidget(page)

    # ----------------------------------------------------------- navigation

    def _open_downloader(self, platform, audio_only=False):
        if audio_only:
            self.video_title_lbl.setText(f"{platform} Downloader")
        else:
            self.video_title_lbl.setText(f"{platform} Video Downloader")
        if audio_only != self.audio_only:
            # switching modes invalidates a save path picked with the other extension
            self.video_save_path = ""
            self.video_path_lbl.setText("No file selected")
        self.audio_only = audio_only
        self.stacked_widget.setCurrentIndex(1)

    # ----------------------------------------------------------- video logic

    def _pick_video_save_path(self):
        if self.audio_only:
            caption, name, file_filter, ext = "Save Audio As", "audio.mp3", "MP3 Audio (*.mp3)", ".mp3"
        else:
            caption, name, file_filter, ext = "Save Video As", "video.mp4", "MP4 Video (*.mp4)", ".mp4"
        path, _ = QFileDialog.getSaveFileName(
            self, caption,
            os.path.join(os.path.expanduser("~/Desktop"), name),
            file_filter
        )
        if path:
            if not path.lower().endswith(ext):
                path += ext
            self.video_save_path = path
            self.video_path_lbl.setText(path)

    def _start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a valid URL.")
            return
        if not self.video_save_path:
            QMessageBox.warning(self, "Error", "Please choose where to save the file.")
            return

        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading...")
        self.video_progress.setValue(0)
        self.video_progress.setVisible(True)
        self.video_status_lbl.setText("Starting...")
        self.video_status_lbl.setVisible(True)

        self.download_worker = DownloadWorker(url, self.video_save_path, self.audio_only)
        self.download_worker.progress.connect(self.video_progress.setValue)
        self.download_worker.status_msg.connect(self.video_status_lbl.setText)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.start()

    def _on_download_finished(self, success, error_msg):
        self.video_progress.setVisible(False)
        self.video_status_lbl.setVisible(False)
        self.download_btn.setText("Download")
        self.download_btn.setEnabled(True)

        if success:
            QMessageBox.information(self, "Success", f"Saved to:\n{self.video_save_path}")
            self.url_input.clear()
            self.video_save_path = ""
            self.video_path_lbl.setText("No file selected")
        else:
            QMessageBox.critical(self, "Error", f"Download failed:\n{error_msg}")

    # ----------------------------------------------------------- PDF logic

    def _browse_docx(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select .docx Files", "", "Word Documents (*.docx)")
        if files:
            self.drop_zone.add_files(files)

    def _pick_pdf_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Directory")
        if folder:
            self.pdf_dest_path = folder
            self.pdf_dest_lbl.setText(folder)

    def _convert_pdfs(self):
        files = self.drop_zone.selected_files
        if not files:
            QMessageBox.warning(self, "Error", "Please select at least one .docx file.")
            return
        if not self.pdf_dest_path:
            QMessageBox.warning(self, "Error", "Please select a destination directory.")
            return

        self.convert_btn.setText("Converting...")
        self.convert_btn.setEnabled(False)
        self.pdf_progress.setValue(0)
        self.pdf_progress.setVisible(True)
        QApplication.processEvents()

        try:
            for i, file in enumerate(files):
                name = os.path.splitext(os.path.basename(file))[0]
                out = os.path.join(self.pdf_dest_path, f"{name}.pdf")
                convert_docx_to_pdf(file, out)
                self.pdf_progress.setValue(int((i + 1) / len(files) * 100))
                QApplication.processEvents()

            QMessageBox.information(self, "Success", f"Converted {len(files)} file(s) successfully!")
            self.drop_zone.selected_files = []
            self.drop_zone.setText("Drag and Drop .docx Files Here")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Conversion failed:\n{str(e)}")
        finally:
            self.pdf_progress.setVisible(False)
            self.convert_btn.setText("Convert to PDF")
            self.convert_btn.setEnabled(True)

    # ----------------------------------------------------------- image logic

    def _browse_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Images (" + " ".join("*" + e for e in IMAGE_EXTS) + ")"
        )
        if files:
            self.image_drop_zone.add_files(files)

    def _pick_image_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Directory")
        if folder:
            self.image_dest_path = folder
            self.image_dest_lbl.setText(folder)

    def _convert_images(self):
        files = self.image_drop_zone.selected_files
        if not files:
            QMessageBox.warning(self, "Error", "Please select at least one image.")
            return
        if not self.image_dest_path:
            QMessageBox.warning(self, "Error", "Please select a destination directory.")
            return

        ext = "." + self.image_format.currentText().lower()
        self.image_convert_btn.setText("Converting...")
        self.image_convert_btn.setEnabled(False)
        self.image_progress.setValue(0)
        self.image_progress.setVisible(True)
        QApplication.processEvents()

        try:
            for i, file in enumerate(files):
                name = os.path.splitext(os.path.basename(file))[0]
                out = os.path.join(self.image_dest_path, f"{name}{ext}")
                if os.path.abspath(out) == os.path.abspath(file):
                    out = os.path.join(self.image_dest_path, f"{name}_converted{ext}")
                convert_image(file, out, self.image_width.value(), self.image_quality.value())
                self.image_progress.setValue(int((i + 1) / len(files) * 100))
                QApplication.processEvents()

            QMessageBox.information(self, "Success", f"Converted {len(files)} image(s) successfully!")
            self.image_drop_zone.selected_files = []
            self.image_drop_zone.setText("Drag and Drop Images Here")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Conversion failed:\n{str(e)}")
        finally:
            self.image_progress.setVisible(False)
            self.image_convert_btn.setText("Convert Images")
            self.image_convert_btn.setEnabled(True)

    # ----------------------------------------------------------- PDF merge logic

    def _browse_merge_pdfs(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDF Files", "", "PDF Files (*.pdf)")
        if files:
            self.merge_list.add_files(files)

    def _merge_pdfs(self):
        files = self.merge_list.paths()
        if len(files) < 2:
            QMessageBox.warning(self, "Error", "Please add at least two PDF files.")
            return

        out, _ = QFileDialog.getSaveFileName(
            self, "Save Merged PDF As",
            os.path.join(os.path.expanduser("~/Desktop"), "merged.pdf"),
            "PDF Files (*.pdf)"
        )
        if not out:
            return
        if not out.lower().endswith('.pdf'):
            out += '.pdf'

        self.merge_btn.setText("Merging...")
        self.merge_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            merge_pdfs(files, out)
            QMessageBox.information(self, "Success", f"Merged {len(files)} PDFs into:\n{out}")
            self.merge_list.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Merge failed:\n{str(e)}")
        finally:
            self.merge_btn.setText("Merge PDFs")
            self.merge_btn.setEnabled(True)
