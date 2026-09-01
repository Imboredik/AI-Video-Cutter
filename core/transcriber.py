# core/transcriber.py

import os
import soundfile as sf
import torch
import gigaam
import tempfile
import shutil


class GigaAMTranscriber:
    def __init__(self, model_name="v3_e2e_rnnt"):
        """
        Инициализация транскрайбера.

        Args:
            model_name: имя модели GigaAM
                - "e2e_ctc" (быстрее)
                - "e2e_rnnt" (качественнее)
                - "v3_e2e_ctc" (v3, быстрее)
                - "v3_e2e_rnnt" (v3, лучшее качество, рекомендуется)
        """
        print(f"Загрузка модели GigaAM: {model_name}...")
        self.model = gigaam.load_model(model_name, device="cuda")
        print("Модель успешно загружена!")

    def _split_audio(self, audio_path, segment_duration=19):
        """
        Разбивает аудио на сегменты по 19 секунд.
        ВАЖНО: 19 секунд — эмпирически найденное значение,
        при 20 секундах GigaAM выдаёт <unk>.
        """
        print(f"  Разбиваем аудио на сегменты по {segment_duration} сек...")

        waveform, sample_rate = sf.read(audio_path, dtype='float32')
        total_samples = len(waveform)
        segment_samples = int(segment_duration * sample_rate)

        segments = []
        temp_dir = tempfile.mkdtemp(prefix="gigaam_segments_")

        for i, start_sample in enumerate(range(0, total_samples, segment_samples)):
            end_sample = min(start_sample + segment_samples, total_samples)
            segment = waveform[start_sample:end_sample]

            segment_path = os.path.join(temp_dir, f"segment_{i:03d}.wav")
            sf.write(segment_path, segment, sample_rate)
            segments.append(segment_path)

            start_time = start_sample / sample_rate
            end_time = end_sample / sample_rate
            print(f"    Сегмент {i+1}: {start_time:.1f} - {end_time:.1f} сек")

        print(f"  Создано {len(segments)} сегментов")
        return segments

    def transcribe_segment(self, audio_path, segment_offset=0):
        """
        Распознаёт аудио, разбивая на сегменты по 19 секунд.
        Возвращает список слов с временными метками.

        Args:
            audio_path: путь к аудиофайлу
            segment_offset: смещение времени для этого сегмента (в секундах)

        Returns:
            list: [{'word': str, 'start': float, 'end': float}, ...]
        """
        print(f"Распознавание {os.path.basename(audio_path)}...")

        info = sf.info(audio_path)
        print(f"  Длительность: {info.duration:.1f} сек")

        if torch.cuda.is_available():
            print(f"  GPU: {torch.cuda.get_device_name(0)}")

        # Если аудио длиннее 25 секунд — разбиваем на сегменты
        if info.duration > 25:
            print(f"  Разбиваем на сегменты по 19 секунд...")
            segment_paths = self._split_audio(audio_path, segment_duration=19)

            all_words = []
            segment_start_time = 0

            for seg_path in segment_paths:
                try:
                    print(f"    Обработка {os.path.basename(seg_path)}...")
                    result = self.model.transcribe(seg_path, word_timestamps=True)

                    if result and hasattr(result, 'words'):
                        words = result.words
                        for word in words:
                            word.start += segment_start_time + segment_offset
                            word.end += segment_start_time + segment_offset
                        all_words.extend(words)
                        print(f"      Добавлено {len(words)} слов")
                except Exception as e:
                    print(f"      ❌ Ошибка: {e}")

                segment_start_time += 19  # Важно: 19 секунд!

            # Удаляем временные файлы
            shutil.rmtree(os.path.dirname(segment_paths[0]), ignore_errors=True)

            # Сортируем по времени
            all_words.sort(key=lambda w: w.start)

            # Формируем результат
            word_timings = []
            for word in all_words:
                word_timings.append({
                    'word': word.text,
                    'start': word.start,
                    'end': word.end
                })

            print(f"  ✅ Добавлено {len(word_timings)} слов")
            return word_timings

        else:
            # Короткое аудио — распознаём напрямую
            print(f"  Короткое аудио ({info.duration:.1f} сек), распознаём напрямую...")
            result = self.model.transcribe(audio_path, word_timestamps=True)

            if not result or not hasattr(result, 'words'):
                return []

            word_timings = []
            for word in result.words:
                word_timings.append({
                    'word': word.text,
                    'start': word.start + segment_offset,
                    'end': word.end + segment_offset
                })

            print(f"  ✅ Добавлено {len(word_timings)} слов")
            return word_timings


# Для быстрого тестирования
if __name__ == "__main__":
    TEST_AUDIO = "D:/Progects/videoCutter/audio/progon3.wav"

    if not os.path.exists(TEST_AUDIO):
        print(f"⚠️ Файл не найден: {TEST_AUDIO}")
    else:
        print("🚀 Запуск распознавания...")
        transcriber = GigaAMTranscriber(model_name="v3_e2e_rnnt")
        words = transcriber.transcribe_segment(TEST_AUDIO)

        if words:
            print(f"\n✅ Распознано {len(words)} слов.")
            print("\n📝 Первые 20 слов с таймкодами:")
            for w in words[:20]:
                print(f"  [{w['start']:.2f} - {w['end']:.2f}] {w['word']}")
        else:
            print("⚠️ Не удалось распознать текст.")