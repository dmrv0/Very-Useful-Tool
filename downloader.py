import imageio_ffmpeg
import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal


class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    status_msg = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, output_path, audio_only=False):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.audio_only = audio_only

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
            self.status_msg.emit("Converting to MP3..." if self.audio_only else "Merging streams...")

    def run(self):
        try:
            ydl_opts = {
                'outtmpl': self.output_path,
                # prefer H.264 + AAC so the mp4 plays in any default player
                # (AV1/VP9 often don't); fall back to the best streams otherwise.
                # merge_output_format converts everything to mp4
                'format': 'bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                # bundled ffmpeg, so merging works without a system install
                'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
                'nocheckcertificate': True,
                'progress_hooks': [self._progress_hook],
                'quiet': True,
            }
            if self.audio_only:
                # yt-dlp picks the extension, then FFmpegExtractAudio swaps it for .mp3
                base = self.output_path[:-4] if self.output_path.lower().endswith('.mp3') else self.output_path
                ydl_opts['outtmpl'] = base + '.%(ext)s'
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))
