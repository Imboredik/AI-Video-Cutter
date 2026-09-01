# core/video_processor.py

import os
import subprocess
from pathlib import Path
from config import Config


class VideoProcessor:
    """Класс для работы с видео (извлечение аудио, превью)."""

    @staticmethod
    def extract_audio(video_path, output_dir=None):
        """
        Извлекает аудио из видео в WAV (16kHz, моно).
        Возвращает путь к аудиофайлу.
        """
        if output_dir is None:
            output_dir = Config.TEMP_DIR

        os.makedirs(output_dir, exist_ok=True)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(output_dir, f"{video_name}.wav")

        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '16000', '-ac', '1',
            '-y', audio_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return audio_path

    @staticmethod
    def extract_thumbnail(video_path, output_dir=None, size=(200, 200)):
        """
        Извлекает первый кадр видео и сжимает до указанного размера.
        Возвращает путь к миниатюре.
        """
        if output_dir is None:
            output_dir = Config.TEMP_DIR

        os.makedirs(output_dir, exist_ok=True)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        thumbnail_path = os.path.join(output_dir, f"{video_name}_thumb.jpg")

        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f"thumbnail,scale={size[0]}:{size[1]}",
            '-vframes', '1',
            '-y', thumbnail_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return thumbnail_path

    @staticmethod
    def get_video_info(video_path):
        """
        Возвращает информацию о видео (длительность, разрешение, размер).
        """
        import json
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration,size',
            '-show_entries', 'stream=width,height,codec_name',
            '-of', 'json',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)

        info = {
            'duration': float(data['format']['duration']),
            'size': int(data['format']['size']),
            'width': 0,
            'height': 0,
            'codec': 'unknown'
        }

        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                info['width'] = int(stream.get('width', 0))
                info['height'] = int(stream.get('height', 0))
                info['codec'] = stream.get('codec_name', 'unknown')
                break

        return info