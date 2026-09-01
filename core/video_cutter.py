# core/video_cutter.py

import os
import subprocess
import shutil
from core.signals import signals


class VideoCutter:
    def __init__(self, use_gpu=True):
        self.use_gpu = use_gpu and self._check_nvenc()
        self.temp_files = []
        self.is_running = True
        self.BUFFER = 0.5  # 1 секунда запаса
        print(use_gpu)

    def _check_nvenc(self):
        try:
            result = subprocess.run(
                ['ffmpeg', '-encoders'],
                capture_output=True, text=True, timeout=5,
                encoding='utf-8', errors='ignore'
            )
            return 'h264_nvenc' in result.stdout or 'h264_nvenc' in result.stderr
        except:
            return False

    def _get_gpu_params(self):
        return [
            '-c:v', 'h264_nvenc',
            '-preset', 'p1',
            '-rc', 'vbr',
            '-cq', '23',
            '-b:v', '0',
            '-profile:v', 'high',
            '-pix_fmt', 'yuv420p',
        ]

    def _get_cpu_params(self):
        return [
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
        ]

    def _get_audio_params(self):
        return [
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
        ]

    def _rough_cut(self, video_path, start, end, output_path):
        """
        Шаг 1: Грубая нарезка с запасом (+BUFFER секунд).
        Использует -c copy (без перекодирования) — быстро!
        """
        rough_start = max(0, start - self.BUFFER)
        rough_end = end + self.BUFFER

        print(f"[DEBUG] _rough_cut: {rough_start} -> {rough_end} -> {output_path}")

        cmd = [
            'ffmpeg',
            '-ss', str(rough_start),
            '-i', video_path,
            '-to', str(rough_end),
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            '-y',
            output_path
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
                encoding='utf-8', errors='ignore'
            )
            return result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0
        except Exception as e:
            print(f"[VIDEO_CUTTER] Грубая нарезка ошибка: {e}")
            return False

    def _exact_cut(self, rough_path, start, end, output_path):
        """Шаг 2: Точная обрезка — убираем лишнюю секунду."""

        # 👇 ПРОВЕРКА
        print(f"[DEBUG] _exact_cut: rough_path={rough_path}")
        print(f"[DEBUG] _exact_cut: exists={os.path.exists(rough_path)}")
        if os.path.exists(rough_path):
            print(f"[DEBUG] _exact_cut: size={os.path.getsize(rough_path)} bytes")

        local_start = self.BUFFER
        local_end = self.BUFFER + (end - start)
        print(f"[DEBUG] _exact_cut: local_start={local_start}, local_end={local_end}")

        cmd = [
            'ffmpeg',
            '-i', rough_path,
            '-ss', str(local_start),
            '-to', str(local_end),
        ]

        if self.use_gpu:
            cmd.extend(self._get_gpu_params())
        else:
            cmd.extend(self._get_cpu_params())

        cmd.extend(self._get_audio_params())
        cmd.extend(['-y', output_path])

        # print(f"[DEBUG] _exact_cut: cmd={' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=180,
                encoding='utf-8', errors='ignore'
            )
            print(f"[DEBUG] _exact_cut returncode: {result.returncode}")
            if result.returncode != 0:
                print(f"[DEBUG] _exact_cut stdout: {result.stdout[:500]}")
                print(f"[DEBUG] _exact_cut stderr FULL: {result.stderr}")  # 👈 БЕЗ ОБРЕЗКИ
            return result.returncode == 0
        except Exception as e:
            print(f"[DEBUG] _exact_cut exception: {e}")
            return False

    def _concatenate_segments(self, segment_files, output_path):
        """Шаг 3: Склейка сегментов на GPU."""
        concat_file = os.path.abspath("temp_concat.txt")
        with open(concat_file, 'w', encoding='utf-8') as f:
            for seg_file in segment_files:
                f.write(f"file '{os.path.abspath(seg_file)}'\n")

        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
        ]

        if self.use_gpu:
            cmd.extend(self._get_gpu_params())
        else:
            cmd.extend(self._get_cpu_params())

        cmd.extend(self._get_audio_params())
        cmd.extend(['-y', output_path])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600,
                encoding='utf-8', errors='ignore'
            )
            os.remove(concat_file)
            return result.returncode == 0
        except Exception as e:
            try:
                os.remove(concat_file)
            except:
                pass
            print(f"[VIDEO_CUTTER] Склейка ошибка: {e}")
            return False

    def cut_by_timelines(self, video_path, timelines, output_path, separate=False):
        """Основной метод: грубая нарезка → точная обрезка → склейка."""
        self.is_running = True
        self.temp_files = []
        results = []

        try:

            # print(f"[DEBUG] video_path: {video_path}")
            # print(f"[DEBUG] output_path: {output_path}")
            # print(f"[DEBUG] timelines: {timelines}")
            # print(f"[DEBUG] os.path.exists(video_path): {os.path.exists(video_path)}")

            if not os.path.exists(video_path):
                raise Exception(f"Видео не найдено: {video_path}")

            signals.montage_status.emit("Начинаем монтаж...")
            signals.montage_progress.emit(10)

            if not timelines:
                raise Exception("Нет таймкодов для монтажа")

            if not os.path.exists(video_path):
                raise Exception(f"Видео не найдено: {video_path}")

            sorted_timelines = sorted(timelines, key=lambda x: x['start'])
            total = len(sorted_timelines)

            if separate:
                base_name = os.path.splitext(output_path)[0]
                ext = os.path.splitext(output_path)[1]

                for i, tl in enumerate(sorted_timelines, 1):
                    if not self.is_running:
                        raise Exception("Монтаж отменён пользователем")

                    start = tl['start']
                    end = tl['end']
                    desc = tl.get('description', f'Фрагмент {i}')

                    safe_desc = self._sanitize_filename(desc)
                    rough_path = os.path.abspath(f"temp_rough_{i:03d}.mp4")
                    self.temp_files.append(rough_path)

                    seg_output = f"{base_name}_{i:02d}_{safe_desc}{ext}"

                    signals.montage_status.emit(f"Грубая нарезка {i}/{total}: {desc[:30]}...")
                    signals.montage_progress.emit(20 + int((i / total) * 30))

                    # Шаг 1: Грубая нарезка (быстро, CPU)
                    if not self._rough_cut(video_path, start, end, rough_path):
                        signals.montage_log.emit(f"❌ Грубая нарезка {i} ошибка")
                        continue

                    signals.montage_status.emit(f"Точная обрезка {i}/{total}: {desc[:30]}...")
                    signals.montage_progress.emit(30 + int((i / total) * 40))

                    # Шаг 2: Точная обрезка (GPU)
                    if self._exact_cut(rough_path, start, end, seg_output):
                        results.append(seg_output)
                        signals.montage_log.emit(f"✅ Фрагмент {i}: {desc[:50]}")
                    else:
                        signals.montage_log.emit(f"❌ Точная обрезка {i} ошибка")

                if not results:
                    raise Exception("Не удалось вырезать ни одного фрагмента")

            else:
                segment_files = []

                for i, tl in enumerate(sorted_timelines, 1):
                    if not self.is_running:
                        raise Exception("Монтаж отменён пользователем")

                    start = tl['start']
                    end = tl['end']
                    desc = tl.get('description', f'Фрагмент {i}')

                    rough_path = os.path.abspath(f"temp_rough_{i:03d}.mp4")
                    seg_path = os.path.abspath(f"temp_segment_{i:03d}.mp4")
                    self.temp_files.extend([rough_path, seg_path])

                    signals.montage_status.emit(f"Грубая нарезка {i}/{total}: {desc[:30]}...")
                    signals.montage_progress.emit(20 + int((i / total) * 30))

                    # Шаг 1: Грубая нарезка (быстро, CPU)
                    if not self._rough_cut(video_path, start, end, rough_path):
                        signals.montage_log.emit(f"❌ Грубая нарезка {i} ошибка")
                        continue

                    signals.montage_status.emit(f"Точная обрезка {i}/{total}: {desc[:30]}...")
                    signals.montage_progress.emit(30 + int((i / total) * 40))

                    # Шаг 2: Точная обрезка (GPU)
                    if self._exact_cut(rough_path, start, end, seg_path):
                        segment_files.append(seg_path)
                        signals.montage_log.emit(f"✅ Фрагмент {i}: {desc[:50]}")
                    else:
                        signals.montage_log.emit(f"❌ Точная обрезка {i} ошибка")

                if not segment_files:
                    raise Exception("Не удалось вырезать ни одного фрагмента")

                signals.montage_status.emit("Склеиваем фрагменты...")
                signals.montage_progress.emit(80)

                # Шаг 3: Склейка (GPU)
                if self._concatenate_segments(segment_files, output_path):
                    results.append(output_path)
                else:
                    raise Exception("Ошибка при склейке сегментов")

            signals.montage_progress.emit(100)
            signals.montage_status.emit("✅ Монтаж завершён!")

            if results:
                size_mb = os.path.getsize(results[0]) / (1024 * 1024)
                signals.montage_log.emit(f"✅ Видео создано: {results[0]} ({size_mb:.1f} MB)")

            return results

        except Exception as e:
            signals.montage_error.emit(str(e))
            raise
        finally:
            self._cleanup_temp_files()

    def _sanitize_filename(self, name):
        invalid = '<>:"/\\|?*'
        for char in invalid:
            name = name.replace(char, '_')
        if len(name) > 40:
            name = name[:40]
        return name.replace(' ', '_')

    def _cleanup_temp_files(self):
        for f in self.temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass

        import glob
        for pattern in ["temp_rough_*.mp4", "temp_segment_*.mp4", "temp_concat*.txt"]:
            for f in glob.glob(pattern):
                try:
                    os.remove(f)
                except:
                    pass

    def stop(self):
        self.is_running = False