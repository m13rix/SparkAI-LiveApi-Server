import requests
from connection_manager import manager

# Ваш AppID, полученный в Wolfram|Alpha Developer Portal
APP_ID = 'LQR5EK-UL8EAEWKA2'

# Базовый URL LLM API
url = 'https://www.wolframalpha.com/api/v1/llm-api'

async def wolfram(args):
    # Параметры запроса
    params = {
        'appid': APP_ID,  # обязательно для аутентификации :contentReference[oaicite:0]{index=0}
        'input': args.get('query'),  # сам запрос, string :contentReference[oaicite:1]{index=1}
        # 'maxchars': '500',    # опционально: ограничение длины ответа :contentReference[oaicite:2]{index=2}
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # бросит исключение при HTTP-ошибке
        # Ответ возвращается в чистом текстовом виде, готовом для употребления LLM
        print('Ответ от Wolfram|Alpha LLM API:')
        print(response.text)
        await manager.send_instruction(
            session_id=args.get('session_id'),
            instruction_type="SET",
            function_name='wolfram',
            args={ 'output': response.text },
            request_id="unique-request-id-123"
        )
        return response.text
    except requests.exceptions.HTTPError as errh:
        print(f'HTTP ошибка: {errh} — {response.text}')
        return f'HTTP ошибка: {errh} — {response.text}'
    except requests.exceptions.RequestException as err:
        print(f'Ошибка запроса: {err}')
        return f'Ошибка запроса: {err}'