from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.ws.manager import manager

ws_router = APIRouter()


@ws_router.websocket("/ws/projects/{project_id}")
async def ws_project(project_id: str, websocket: WebSocket):
    await manager.subscribe_project(project_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive, ignore incoming
    except WebSocketDisconnect:
        manager.unsubscribe_project(project_id, websocket)


@ws_router.websocket("/ws/cards/{card_id}")
async def ws_card(card_id: str, websocket: WebSocket):
    await manager.subscribe_card(card_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.unsubscribe_card(card_id, websocket)
