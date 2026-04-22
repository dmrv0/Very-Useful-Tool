import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QHBoxLayout, QStackedWidget, QMessageBox,
    QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont

from downloader import DownloadWorker
from pdf_utils import convert_docx_to_pdf


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
    def __init__(self, title):
        super().__init__(title)
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
        valid = [f for f in files if f.lower().endswith('.docx')]
        self.selected_files.extend(valid)
        if self.selected_files:
            names = [os.path.basename(f) for f in self.selected_files]
            preview = ", ".join(names[:3]) + ("..." if len(names) > 3 else "")
            self.setText(f"Selected {len(self.selected_files)} files:\n{preview}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Tool Application")
        self.resize(560, 520)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self._setup_main_menu()
        self._setup_video_downloader()
        self._setup_pdf_converter()

        self.download_worker = None
        self.video_save_path = ""
        self.pdf_dest_path = ""

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

        btn_pdf = QPushButton("Word to PDF Converter")
        btn_pdf.setStyleSheet(BTN_STYLE)
        btn_pdf.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))

        layout.addWidget(btn_yt)
        layout.addWidget(btn_tw)
        layout.addWidget(btn_pdf)

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

    # ----------------------------------------------------------- navigation

    def _open_downloader(self, platform):
        self.video_title_lbl.setText(f"{platform} Video Downloader")
        self.stacked_widget.setCurrentIndex(1)

    # ----------------------------------------------------------- video logic

    def _pick_video_save_path(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Video As",
            os.path.expanduser("~/Desktop/video.mp4"),
            "MP4 Video (*.mp4)"
        )
        if path:
            if not path.endswith('.mp4'):
                path += '.mp4'
            self.video_save_path = path
            self.video_path_lbl.setText(path)

    def _start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a valid URL.")
            return
        if not self.video_save_path:
            QMessageBox.warning(self, "Error", "Please choose where to save the video.")
            return

        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading...")
        self.video_progress.setValue(0)
        self.video_progress.setVisible(True)
        self.video_status_lbl.setText("Starting...")
        self.video_status_lbl.setVisible(True)

        self.download_worker = DownloadWorker(url, self.video_save_path)
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
            QMessageBox.information(self, "Success", f"Video saved to:\n{self.video_save_path}")
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
