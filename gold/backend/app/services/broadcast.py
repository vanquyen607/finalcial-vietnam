from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class Hub:
    """Quản lý kết nối WebSocket và broadcast JSON."""

    def __init__(self) -> None:
        self._clients: dict[WebSocket, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, topics: set[str]) -> None:
        await ws.accept()
        async with self._lock:
            self._clients[ws] = topics

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.pop(ws, None)

    async def set_topics(self, ws: WebSocket, topics: set[str]) -> None:
        async with self._lock:
            if ws in self._clients:
                self._clients[ws] = topics

    @property
    def count(self) -> int:
        return len(self._clients)

    async def broadcast(self, message: dict[str, Any], topic: str = "quote") -> int:
        """Gửi tới client đang subscribe topic. Trả về số client nhận được."""
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        async with self._lock:
            targets = [ws for ws, topics in self._clients.items()
                       if topic in topics or "*" in topics]
        dead: list[WebSocket] = []
        sent = 0
        for ws in targets:
            try:
                await ws.send_text(payload)
                sent += 1
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)
        return sent


hub = Hub()
