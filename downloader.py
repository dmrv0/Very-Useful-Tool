import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal


class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    status_msg = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, output_path):
        super().__init__()
        self.url = url
        self.output_path = output_path

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                self.progress.emit(int(downloaded / total * 100))
            speed = d.get('speed')
            if speed:
                self.status_msg.emit(f"Downloading... {speed / 1048576:.1f} MB/s")
        elif d['status'] == 'finished':
            self.progress.emit(99)
            self.status_msg.emit("Merging streams...")

    def run(self):
        try:
            ydl_opts = {
                'outtmpl': self.output_path,
                # bestvideo+bestaudio lets ffmpeg pick the best streams;
                # merge_output_format converts everything to mp4
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'extractor_args': {
                    'youtube': {
                        # tv_embedded is the most reliable client without a PO Token
                        'player_client': ['tv_embedded'],
                    }
                },
                'nocheckcertificate': True,
                'progress_hooks': [self._progress_hook],
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))
