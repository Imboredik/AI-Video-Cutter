# core/llm_client.py

import os
import json
import re
from datetime import datetime
from openai import OpenAI
from config import Config
from core.signals import signals


class LLMClient:
    """Клиент для работы с LLM (Qwen3.5-Flash)."""

    def __init__(self):
        self.api_key = os.getenv("QWEN_API_KEY")
        self.base_url = os.getenv("QWEN_API_URL", "https://api.vsellm.ru/v1")
        self.model = os.getenv("QWEN_MODEL", "qwen/qwen3.5-flash")
        self.system_prompt = self._get_system_prompt()
        self.context = []  # история чата + транскрипция

        if not self.api_key:
            raise ValueError("QWEN_API_KEY не найден в .env файле")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def _get_system_prompt(self):
        """Возвращает системный промпт для LLM."""
        return """
        Ты — ассистент для видеомонтажа. Твоя задача — помогать пользователю находить интересные моменты в видео.

        Ты получишь транскрипцию видео с временными метками в формате [ЧЧ:ММ:СС] [ЧЧ:ММ:СС] слово.

        **Правила:**
        1. Отвечай всегда на русском языке.
        2. Если пользователь просит найти фрагменты — верни таймкоды в формате:
           [ЧЧ:ММ:СС] [ЧЧ:ММ:СС]
           Каждая пара таймкодов на отдельной строке.
        3. Ты можешь возвращать несколько пар таймкодов.
        4. К каждому ответу добавляй краткое описание того, что происходит в этом фрагменте.
        5. Всегда добавляй по 2 секунде в начало и конец к выбранному фрагменту.
        6. Если выбранные фрагменты накладываются друг на друга по временным меткам, то нужно превратить такие фрагменты в один.
        6. Если пользователь просит что-то, что не связано с поиском фрагментов — просто ответь на вопрос.
        7. Всегда используй транскрипцию с таймкодами для поиска фрагментов.
        8. Транскрипция уже есть в контексте, НЕ ПРОСИ пользователя отправить её повторно.
         

        **Пример ответа с таймкодами:**
        Я нашёл несколько интересных моментов:

        [00:12:30] [00:15:45] — стример обсуждает новую игру
        [00:45:10] [00:47:20] — эмоциональный момент с реакцией зрителей
        [01:20:00] [01:22:30] — люди в подкасте обсуждают тему X

        **Важно:** Всегда возвращай таймкоды в формате [ЧЧ:ММ:СС] [ЧЧ:ММ:СС].
        """

    def _format_transcription(self, words):
        """Форматирует транскрипцию в [ЧЧ:ММ:СС] [ЧЧ:ММ:СС] слово."""
        lines = []
        for w in words:
            start = self._seconds_to_hms(w['start'])
            end = self._seconds_to_hms(w['end'])
            lines.append(f"[{start}] [{end}] {w['word']}")
        return "\n".join(lines)

    def _seconds_to_hms(self, seconds):
        """Конвертирует секунды в ЧЧ:ММ:СС."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def get_initial_message(self, transcription_text, video_name):
        """Генерирует приветственное сообщение после транскрибации."""
        return {
            'role': 'assistant',
            'content': f"""
**🎬 Транскрипция видео "{video_name}" завершена!**

📝 **Краткая сводка:**
{self._summarize(transcription_text)}

💡 **Что я умею:**
• Находить моменты по вашему запросу
• Выделять диалоги, эмоции, игры
• Собирать лучшие моменты в нарезку

✍️ **Примеры запросов:**
• "Найди все моменты, где стример говорит о новой игре"
• "Покажи фрагменты, где стример смеётся или злится"
• "Выдели диалоги между стримером и зрителями"
• "Собери все моменты с PvP боями"

**Просто напишите, что хотите найти!** 👇
"""
        }

    def _summarize(self, text, max_len=500):
        """Обрезает текст для краткой сводки."""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    def set_context_from_history(self, chat_history):
        """Устанавливает контекст из сохранённой истории чата."""
        self.context = []
        for msg in chat_history:
            role = msg['role']
            content = msg['content']
            if role == "👤 Вы":
                self.context.append({"role": "user", "content": content})
            elif role == "🤖 ИИ":
                self.context.append({"role": "assistant", "content": content})

    def send_message(self, user_message, transcription_text, video_name, words=None):
        """
        Отправляет сообщение в LLM.
        """
        signals.llm_status.emit("Обработка запроса...")
        signals.llm_progress.emit(10)

        # Если контекст пустой — добавляем транскрипцию
        if not self.context:
            # Форматируем транскрипцию с таймкодами
            if words:
                formatted_transcription = self._format_transcription(words)
            else:
                formatted_transcription = transcription_text

            # Логируем начальный запрос
            self._log_initial_request(video_name, formatted_transcription)

            # Сохраняем транскрипцию в контекст (как system)
            self.context.append({
                "role": "system",
                "content": f"Вот транскрипция видео '{video_name}':\n\n{formatted_transcription}\n\nИспользуй эту транскрипцию для всех последующих ответов. Не проси пользователя отправить её повторно."
            })

        # Формируем сообщения
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        messages.extend(self.context)
        messages.append({"role": "user", "content": user_message})

        signals.llm_progress.emit(50)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )

            signals.llm_progress.emit(90)

            raw_response = response.choices[0].message.content

            # Сохраняем историю диалога
            self.context.append({"role": "user", "content": user_message})
            self.context.append({"role": "assistant", "content": raw_response})

            # Парсим таймкоды
            timelines = self._parse_timelines(raw_response)

            # Логируем запрос
            self._log_request(user_message, raw_response, timelines)

            signals.llm_progress.emit(100)
            signals.llm_status.emit("Готово")

            return {
                'response': raw_response,
                'timelines': timelines,
                'query': user_message,
                'full_response': raw_response
            }

        except Exception as e:
            signals.llm_error.emit(str(e))
            raise

    def _parse_timelines(self, response):
        """Парсит таймкоды из ответа LLM."""
        timelines = []
        pattern = r'\[(\d{2}):(\d{2}):(\d{2})\]\s*\[(\d{2}):(\d{2}):(\d{2})\]\s*—?\s*(.*?)(?=\n|$)'
        matches = re.findall(pattern, response, re.MULTILINE)

        for match in matches:
            h1, m1, s1, h2, m2, s2, desc = match
            start_sec = int(h1)*3600 + int(m1)*60 + int(s1)
            end_sec = int(h2)*3600 + int(m2)*60 + int(s2)
            if start_sec < end_sec:
                timelines.append({
                    'start': start_sec,
                    'end': end_sec,
                    'description': desc.strip() or "Фрагмент"
                })

        return timelines

    def _log_initial_request(self, video_name, formatted_transcription):
        """Логирует начальный запрос с транскрипцией."""
        log_dir = os.path.join(Config.LOG_DIR, "llm")
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"initial_context_{timestamp}.json")

        data = {
            'timestamp': timestamp,
            'video_name': video_name,
            'transcription_length': len(formatted_transcription),
            'transcription_preview': formatted_transcription[:500] + "..." if len(formatted_transcription) > 500 else formatted_transcription
        }

        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка логирования начального контекста: {e}")

    def _log_request(self, query, response, timelines):
        """Логирует запрос и ответ в файл."""
        log_dir = os.path.join(Config.LOG_DIR, "llm")
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"request_{timestamp}.json")

        data = {
            'timestamp': timestamp,
            'query': query,
            'response': response,
            'timelines': timelines,
            'context_length': len(self.context)
        }

        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка логирования: {e}")

    def clear_context(self):
        """Очищает историю чата."""
        self.context = []

    def get_context(self):
        """Возвращает историю чата."""
        return self.context