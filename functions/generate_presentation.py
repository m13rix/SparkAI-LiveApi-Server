#!/usr/bin/env python3
import requests
import json
import sys
from typing import Optional


class PresentationClient:
    def __init__(self, server_url: str = "http://localhost:3000"):
        self.server_url = server_url
        self.session_id: Optional[str] = None

    def create_session(self, topic: str, audience: str, notes: str = "",
                       style: str = "modern", ultra_mode: bool = False) -> bool:
        """Создает новую сессию для генерации презентации"""
        try:
            response = requests.post(f"{self.server_url}/api/create-session",
                                     json={
                                         "topic": topic,
                                         "audience": audience,
                                         "notes": notes,
                                         "style": style,
                                         "ultraMode": ultra_mode
                                     })

            if response.status_code == 200:
                data = response.json()
                self.session_id = data["sessionId"]
                print(f"✅ Сессия создана: {self.session_id}")
                return True
            else:
                print(f"❌ Ошибка создания сессии: {response.text}")
                return False
        except requests.RequestException as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def generate_content(self) -> bool:
        """Генерирует содержание презентации"""
        if not self.session_id:
            print("❌ Сессия не создана")
            return False

        try:
            print("\n🔄 Генерация содержания презентации...")
            response = requests.post(f"{self.server_url}/api/generate-content/{self.session_id}",
                                     stream=True)

            if response.status_code == 200:
                print("\n📝 Содержание презентации:")
                print("-" * 50)
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        print(chunk.decode('utf-8'), end='', flush=True)
                print("\n" + "-" * 50)
                return True
            else:
                print(f"❌ Ошибка генерации содержания: {response.text}")
                return False
        except requests.RequestException as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def refine_content(self, feedback: str) -> bool:
        """Уточняет содержание презентации на основе обратной связи"""
        if not self.session_id:
            print("❌ Сессия не создана")
            return False

        try:
            print(f"\n🔄 Уточнение содержания на основе отзыва: {feedback}")
            response = requests.post(f"{self.server_url}/api/refine-content/{self.session_id}",
                                     json={"feedback": feedback},
                                     stream=True)

            if response.status_code == 200:
                print("\n📝 Обновленное содержание презентации:")
                print("-" * 50)
                for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                    if chunk:
                        print(chunk, end='', flush=True)
                print("\n" + "-" * 50)
                return True
            else:
                print(f"❌ Ошибка уточнения содержания: {response.text}")
                return False
        except requests.RequestException as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def approve_content(self) -> bool:
        """Одобряет содержание и переходит к генерации кода"""
        if not self.session_id:
            print("❌ Сессия не создана")
            return False

        try:
            response = requests.post(f"{self.server_url}/api/approve-content/{self.session_id}")

            if response.status_code == 200:
                print("✅ Содержание одобрено, переходим к генерации кода")
                return True
            else:
                print(f"❌ Ошибка одобрения содержания: {response.text}")
                return False
        except requests.RequestException as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def generate_code(self) -> bool:
        """Генерирует код презентации"""
        if not self.session_id:
            print("❌ Сессия не создана")
            return False

        try:
            print("\n🔄 Генерация кода презентации...")
            response = requests.post(f"{self.server_url}/api/generate-code/{self.session_id}",
                                     stream=True)

            if response.status_code == 200:
                print("\n💻 Код презентации:")
                print("-" * 50)
                for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                    if chunk:
                        print(chunk, end='', flush=True)
                print("\n" + "-" * 50)
                return True
            else:
                print(f"❌ Ошибка генерации кода: {response.text}")
                return False
        except requests.RequestException as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def refine_code(self, feedback: str) -> bool:
        """Уточняет код презентации на основе обратной связи"""
        if not self.session_id:
            print("❌ Сессия не создана")
            return False

        try:
            print(f"\n🔄 Уточнение кода на основе отзыва: {feedback}")
            response = requests.post(f"{self.server_url}/api/refine-code/{self.session_id}",
                                     json={"feedback": feedback},
                                     stream=True)

            if response.status_code == 200:
                print("\n💻 Обновленный код презентации:")
                print("-" * 50)
                for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                    if chunk:
                        print(chunk, end='', flush=True)
                print("\n" + "-" * 50)
                return True
            else:
                print(f"❌ Ошибка уточнения кода: {response.text}")
                return False
        except requests.RequestException as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def get_final_result(self) -> Optional[dict]:
        """Получает финальный результат"""
        if not self.session_id:
            print("❌ Сессия не создана")
            return None

        try:
            response = requests.get(f"{self.server_url}/api/get-result/{self.session_id}")

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Ошибка получения результата: {response.text}")
                return None
        except requests.RequestException as e:
            print(f"❌ Ошибка подключения: {e}")
            return None

    def save_presentation(self, filename: str = "presentation.html") -> bool:
        """Сохраняет презентацию в HTML файл"""
        result = self.get_final_result()
        if not result or not result.get("code"):
            print("❌ Нет кода для сохранения")
            return False

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result["code"])
            print(f"✅ Презентация сохранена в файл: {filename}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения файла: {e}")
            return False


def main():
    client = PresentationClient()

    print("🎯 Генератор презентаций")
    print("=" * 40)

    # Сбор параметров презентации
    topic = input("📌 Введите тему презентации: ").strip()
    if not topic:
        print("❌ Тема презентации обязательна")
        return

    audience = input("👥 Введите описание целевой аудитории: ").strip()
    if not audience:
        print("❌ Описание аудитории обязательно")
        return

    notes = input("📝 Введите дополнительные примечания (необязательно): ").strip()

    style = input("🎨 Введите стиль презентации (по умолчанию 'modern'): ").strip()
    if not style:
        style = "modern"

    ultra_mode_input = input("⚡ Включить ультра режим? (y/N): ").strip().lower()
    ultra_mode = ultra_mode_input in ['y', 'yes', 'да']

    # Создание сессии
    if not client.create_session(topic, audience, notes, style, ultra_mode):
        return

    # Генерация содержания
    if not client.generate_content():
        return

    # Цикл уточнения содержания
    while True:
        action = input("\n🤔 Что делать с содержанием?\n"
                       "1. Одобрить и перейти к коду\n"
                       "2. Внести изменения\n"
                       "3. Выйти\n"
                       "Выберите (1-3): ").strip()

        if action == "1":
            if client.approve_content():
                break
            else:
                return
        elif action == "2":
            feedback = input("💬 Введите ваши замечания: ").strip()
            if feedback:
                client.refine_content(feedback)
            else:
                print("❌ Замечания не могут быть пустыми")
        elif action == "3":
            print("👋 До свидания!")
            return
        else:
            print("❌ Неверный выбор, попробуйте снова")

    # Генерация кода
    if not client.generate_code():
        return

    # Цикл уточнения кода
    while True:
        action = input("\n🤔 Что делать с кодом?\n"
                       "1. Принять и сохранить\n"
                       "2. Внести изменения\n"
                       "3. Выйти\n"
                       "Выберите (1-3): ").strip()

        if action == "1":
            filename = input("💾 Введите имя файла (по умолчанию 'presentation.html'): ").strip()
            if not filename:
                filename = "presentation.html"
            if not filename.endswith('.html'):
                filename += '.html'

            if client.save_presentation(filename):
                print("🎉 Презентация готова!")
            break
        elif action == "2":
            feedback = input("💬 Введите ваши замечания: ").strip()
            if feedback:
                client.refine_code(feedback)
            else:
                print("❌ Замечания не могут быть пустыми")
        elif action == "3":
            print("👋 До свидания!")
            return
        else:
            print("❌ Неверный выбор, попробуйте снова")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")