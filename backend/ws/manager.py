from __future__ import annotations
import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # project_id -> set of websockets
        self._project_subs: dict[str, set[WebSocket]] = defaultdict(set)
        # card_id -> set of websockets
        self._card_subs: dict[str, set[WebSocket]] = defaultdict(set)

    async def subscribe_project(self, project_id: str, ws: WebSocket):
        await ws.accept()
        self._project_subs[project_id].add(ws)

    async def subscribe_card(self, card_id: str, ws: WebSocket):
        await ws.accept()
        self._card_subs[card_id].add(ws)

    def unsubscribe_project(self, project_id: str, ws: WebSocket):
        self._project_subs[project_id].discard(ws)

    def unsubscribe_card(self, card_id: str, ws: WebSocket):
        self._card_subs[card_id].discard(ws)

    async def broadcast_project(self, project_id: str, payload: dict):
        message = json.dumps(payload)
        dead: set[WebSocket] = set()
        for ws in list(self._project_subs.get(project_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self._project_subs[project_id] -= dead

    async def broadcast_card(self, card_id: str, payload: dict):
        message = json.dumps(payload)
        dead: set[WebSocket] = set()
        for ws in list(self._card_subs.get(card_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self._card_subs[card_id] -= dead


manager = ConnectionManager()
