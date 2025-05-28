from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel
from dynamic_function_caller import handle_function_call
import json
from connection_manager import manager
import asyncio
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))
model = "gemini-2.0-flash-live-001"

# Define function declarations
FUNCTION_DECLARATIONS = [
    {
        "name": "text_display",
        "description": "Вы говорите с пользователем голосом, и всё, что вы скажете прозвучит только один раз, если вы не будите нарошно повторять. Для того, чтобы отметить какую-то ВАЖНУЮ ИНФОРМАЦИЮ, текстом, которую нужно читать несколько раз, используйте эту функцию. Например, вас просят сказать определение, рецепт, погоду, ответ в дз и т.п. Функция поддерживает markdown",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string"
                }
            },
            "required": [
                "text"
            ]
        }
    },
    {
    "name": "wolfram",
    "description": "Это llm api Wolfram alpha. Используйте его для всего точного: как калькулятор сложных примеров (уравнений, химических уравнений и всё точное математическое), погоды, исторических фактов, праздников, всего. Например, когда У ВАС СПРАШИВАЮТ: \"Реши это квадратное уравнение\" или \"Какая погода завтра в краснодаре?\". В query пишите ЧЁТКИЕ ИНСТРУКЦИИ В ФОРМАТЕ WOLFRAM ALPHA НА АНГЛИЙСКОМ",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string"
        }
      },
      "required": [
        "query"
      ]
    }
    },
    {
    "name": "web_search",
    "description": "Асинхронно ищет по вашему запросу в “большом” интернете (через DuckDuckGo), извлекает заголовки и основной текст страниц.  **Когда использовать:**  * **Сложные или редкие запросы**, где ни Википедия, ни Wolfram Alpha, ни локальная БД не дают полного ответа. * **Неоднозначные темы** или глубокие статьи, которые могут отсутствовать в узкоспециализированных источниках. * **Проверка фактов** из разных сайтов, когда нужна свежая информация, не попавшая ещё в базы.  **Когда не использовать:**  * Если нужен **краткий факт** или формула — сначала обращайтесь к Wolfram Alpha. * Если вопрос охватывается **статьёй в Википедии** — используйте wikipedia\\_search. * Если информация строго **персональная** — берите из локальной БД пользователя.  **Поведение в диалоге:**  1. Голос ИИ: «Сейчас я поищу в интернете…» 2. Вызывается `web_search` и возвращаются заголовки + ключевые выдержки. 3. ИИ озвучивает и формирует ответ на основе свежих данных.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string"
        }
      },
      "required": [
        "query"
      ]
    }
    }
]

class SessionConfig(BaseModel):
    system_prompt: str
    voice_name: str

def create_genai_config(config: SessionConfig):
    return types.LiveConnectConfig(
        system_instruction=types.Content(
            parts=[types.Part(text=config.system_prompt)]
        ),
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=config.voice_name
                )
            )
        ),
        tools=[types.Tool(
            function_declarations=[
                types.FunctionDeclaration(**fd) for fd in FUNCTION_DECLARATIONS
            ]
        )]
    )

async def _process_function_call(fc, session_id, session):
    # Выполняем функцию в фоне
    result = await handle_function_call(fc, session_id)
    # Отправляем результат обратно в модель
    await session.send_tool_response(function_responses=[
        types.FunctionResponse(
            id=fc.id,
            name=fc.name,
            response=result
        )
    ])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    session_id = "SESSION_ID_HERE"
    await manager.connect(session_id, websocket)
    try:
        config_data = await websocket.receive_text()
        config = SessionConfig(**json.loads(config_data))

        async with client.aio.live.connect(
                model=model,
                config=create_genai_config(config)
        ) as session:
            while True:
                user_text = await websocket.receive_text()
                if user_text.strip().lower() == "exit":
                    await websocket.close()
                    break

                try:
                    data = json.loads(user_text)
                    if isinstance(data, dict) and data.get("type") == "function_response":
                        # Здесь ваша логика обработки function_response
                        print("Получен function_response, обрабатываем отдельно...")
                        # Пример: можно вызвать какую-то функцию
                        manager.handle_function_response(data, session_id)
                        continue  # Пропускаем отправку в модель
                except json.JSONDecodeError:
                    pass  # Это не JSON — отправим как обычный текст модели

                # Отправка обычного пользовательского текста в модель
                await session.send_client_content(
                    turns={"role": "user", "parts": [{"text": user_text}]},
                    turn_complete=True
                )

                function_responses = []
                async for response in session.receive():
                    # Обрабатываем аудио-чанки
                    if response.data is not None:
                        await websocket.send_bytes(response.data)

                    # Обрабатываем вызовы функций
                    if response.tool_call:
                        for fc in response.tool_call.function_calls:  # Запускаем фоновый таск, чтобы не блокировать аудио-стрим
                            asyncio.create_task(_process_function_call(fc, session_id, session))

                    # Отправляем ответы на вызовы функций
                    if function_responses:
                        await session.send_tool_response(
                            function_responses=function_responses
                        )
                        function_responses = []

                    if getattr(response, "event", None) and response.event.type == "turn_end":
                        break

    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()
    finally:
        manager.disconnect(session_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
