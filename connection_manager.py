import json
from typing import Dict, Callable, List, Any
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.event_subscribers: Dict[str, List[Callable[[Any, str], None]]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_instruction(
        self,
        session_id: str,
        instruction_type: str,
        function_name: str,
        args: dict = None,
        request_id: str = None
    ):
        payload = {
            "type": instruction_type,
            "function": function_name,
            "args": args or {},
        }
        if request_id:
            payload["requestId"] = request_id

        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_text(json.dumps(payload))

    def subscribe_to_event(self, event_name: str, callback: Callable[[Any, str], None]):
        if event_name not in self.event_subscribers:
            self.event_subscribers[event_name] = []
        self.event_subscribers[event_name].append(callback)

    async def trigger_event(self, event_name: str, data: Any, session_id: str):
        for callback in self.event_subscribers.get(event_name, []):
            result = callback(data, session_id)
            if callable(result):
                await result  # in case it's async

    async def handle_function_response(self, data: Any, session_id: str):
        await self.trigger_event("function_response", data, session_id)

# глобальный экземпляр
manager = ConnectionManager()
