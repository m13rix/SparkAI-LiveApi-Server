import importlib.util
import json
import os
import sys
from typing import Any, Dict, Optional, Union
import inspect
import traceback
import logging
from google.genai import types
from connection_manager import manager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("function_handler")


class FunctionResult:
    """Класс для представления результата выполнения функции"""

    def __init__(self, success: bool, data: Any = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        result = {"success": self.success}
        if self.data is not None:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        return result


async def handle_function_call(fc: types.FunctionCall, session_id: str) -> Dict[str, Any]:
    """
    Обработка вызовов функций с динамической загрузкой модулей

    Args:
        fc: Объект FunctionCall с полями name (имя функции) и args (аргументы в формате JSON)

    Returns:
        Словарь с результатом выполнения функции
    """
    logger.info(f"Вызвана функция: {fc.name} с параметрами: {fc.args}")

    try:
        # Преобразование JSON-строки аргументов в словарь
        args = {}
        if fc.args:
            try:
                args = json.loads(fc.args) if isinstance(fc.args, str) else fc.args
            except json.JSONDecodeError:
                logger.error(f"Ошибка декодирования JSON аргументов: {fc.args}")
                return FunctionResult(
                    success=False,
                    error=f"Ошибка формата аргументов: невозможно декодировать JSON"
                ).to_dict()

        # Загрузка и выполнение функции
        result = await load_and_execute_function(fc.name, args, session_id)
        return result.to_dict()

    except Exception as e:
        logger.error(f"Ошибка при обработке функции {fc.name}: {str(e)}")
        logger.error(traceback.format_exc())
        return FunctionResult(
            success=False,
            error=f"Внутренняя ошибка: {str(e)}"
        ).to_dict()


async def load_and_execute_function(function_name: str, args: Dict[str, Any], session_id: str) -> FunctionResult:
    """
    Динамически загружает и выполняет функцию из файла

    Args:
        function_name: Имя функции (и файла без расширения .py)
        args: Словарь аргументов для передачи в функцию

    Returns:
        Объект FunctionResult с результатом выполнения
    """
    # Проверка безопасности имени функции
    if not is_valid_function_name(function_name):
        return FunctionResult(
            success=False,
            error=f"Недопустимое имя функции: {function_name}"
        )

    args.setdefault("session_id", session_id)

    # Путь к файлу функции
    function_path = os.path.join(os.path.dirname(__file__), "functions", f"{function_name}.py")

    print("OS PATH: " + function_path)

    # Проверка существования файла
    if not os.path.exists(function_path):
        print("Функция не найдена")
        return FunctionResult(
            success=False,
            error=f"Функция '{function_name}' не найдена"
        )

    try:
        await manager.send_instruction(
            session_id=session_id,
            instruction_type="START",
            function_name=function_name,
            args=args,
            request_id="unique-request-id-123"
        )
        # Загрузка модуля
        module = import_module_from_file(function_path, function_name)

        # Проверка наличия функции в модуле
        if not hasattr(module, function_name):
            return FunctionResult(
                success=False,
                error=f"В модуле '{function_name}' не найдена функция с тем же именем"
            )

        # Получение функции из модуля
        function = getattr(module, function_name)

        # Проверка, что это действительно вызываемая функция
        if not callable(function):
            return FunctionResult(
                success=False,
                error=f"'{function_name}' не является вызываемой функцией"
            )

        # Проверка, является ли функция асинхронной
        is_async = inspect.iscoroutinefunction(function)

        # Выполнение функции
        if is_async:
            result = await function(args)
        else:
            result = function(args)

        return FunctionResult(success=True, data=result)

    except ImportError as e:
        logger.error(f"Ошибка импорта модуля {function_name}: {str(e)}")
        return FunctionResult(
            success=False,
            error=f"Ошибка при загрузке модуля '{function_name}': {str(e)}"
        )
    except Exception as e:
        logger.error(f"Ошибка при выполнении функции {function_name}: {str(e)}")
        logger.error(traceback.format_exc())
        return FunctionResult(
            success=False,
            error=f"Ошибка при выполнении функции '{function_name}': {str(e)}"
        )


def import_module_from_file(file_path: str, module_name: str):
    """
    Импортирует модуль из файла

    Args:
        file_path: Путь к файлу модуля
        module_name: Имя, которое будет присвоено модулю

    Returns:
        Импортированный модуль
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"Не удалось создать спецификацию для модуля из {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    if spec.loader:
        spec.loader.exec_module(module)
    else:
        raise ImportError(f"Загрузчик для модуля {module_name} не найден")

    return module


def is_valid_function_name(name: str) -> bool:
    """
    Проверяет, является ли имя функции безопасным

    Args:
        name: Имя функции для проверки

    Returns:
        True, если имя безопасное, иначе False
    """
    # Базовая проверка на допустимые символы в имени файла/функции
    import re
    return bool(re.match(r'^[a-zA-Z0-9_]+$', name))