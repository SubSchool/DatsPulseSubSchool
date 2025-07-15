import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import logging
from app.bot import bot_manager
from app.api import game_api
from typing import List, Dict

# === Настройка логирования ===
logging.basicConfig(
    level=logging.INFO,
    format='[LOG] %(message)s',
    handlers=[
        logging.FileHandler('backend.log'),
        logging.StreamHandler()
    ]
)

app = FastAPI(title="Ant Colony Bot API")

# === CORS настройки ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === WebSocket соединения ===
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        bot_manager.websockets.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in bot_manager.websockets:
            bot_manager.websockets.remove(websocket)

manager = ConnectionManager()

# === Автоматический запуск бота при старте ===
@app.on_event("startup")
async def startup_event():
    logging.info("FastAPI startup - запускаем бота автоматически")
    asyncio.create_task(bot_manager.start())

# === WebSocket эндпоинт ===
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# === API эндпоинты ===
@app.get("/api/status")
async def get_status():
    """Получить статус бота"""
    return {
        "is_running": bot_manager.is_running,
        "team_id": game_api.team_id,
        "score": bot_manager.state.score if bot_manager.state else 0,
        "turn_no": bot_manager.state.turnNo if bot_manager.state else 0,
        "ants_count": len(bot_manager.state.ants) if bot_manager.state else 0
    }

@app.post("/api/bot/start")
async def start_bot():
    """Запустить бота"""
    if bot_manager.is_running:
        return {"status": "already_running"}
    
    # Запускаем бота в фоне
    asyncio.create_task(bot_manager.start())
    return {"status": "started"}

@app.post("/api/bot/stop")
async def stop_bot():
    """Остановить бота"""
    bot_manager.stop()
    return {"status": "stopped"}

@app.get("/api/map")
async def get_map():
    """Получить текущее состояние карты"""
    if not bot_manager.state:
        return {"error": "No game state available"}
    
    return bot_manager.state.model_dump()

@app.get("/api/arena")
async def get_arena():
    """Получить состояние арены напрямую с сервера"""
    arena_data = await game_api.get_arena()
    if not arena_data:
        return {"error": "Failed to get arena data"}
    
    return arena_data.model_dump()

@app.post("/api/register")
async def register():
    """Зарегистрироваться заново"""
    success = await game_api.register()
    return {"success": success, "team_id": game_api.team_id}

# === Таблица ручной приоритезации (in-memory, для MVP) ===
manual_priority_table: List[Dict] = []

# === Экспортируем таблицу для бота ===
bot_manager.manual_priority_table = manual_priority_table

@app.post("/api/manual_priority")
async def manual_priority(request: Request):
    data = await request.json()
    source = data.get("source")  # {q, r}
    target = data.get("target")  # {q, r}
    if not (source and target):
        return {"error": "source and target required"}
    
    # Найти всех муравьёв на source
    ants = [ant for ant in bot_manager.state.ants if ant.q == source["q"] and ant.r == source["r"]]
    
    # Добавить записи в таблицу
    for ant in ants:
        manual_priority_table.append({
            "ant_id": ant.id,
            "target_q": target["q"],
            "target_r": target["r"],
            "status": False
        })
    
    # === НЕМЕДЛЕННО отправляем движения для ручных целей ===
    if ants and bot_manager.state:
        manual_moves = []
        map_cells = [cell.dict() if hasattr(cell, 'dict') else dict(cell) for cell in bot_manager.state.map]
        map_dict = {(cell['q'], cell['r']): cell for cell in map_cells}
        home_cells = [h if isinstance(h, dict) else h.dict() for h in bot_manager.state.home]
        home_positions = {(h['q'], h['r']) for h in home_cells}
        
        for ant in ants:
            current_pos = (ant.q, ant.r)
            target_pos = (target["q"], target["r"])
            path = bot_manager._find_path(current_pos, target_pos, {}, map_dict, home_positions)
            if path:
                manual_moves.append({
                    'ant': ant.id,
                    'path': path
                })
        
        # Отправляем движения немедленно
        if manual_moves:
            try:
                await game_api.send_moves(manual_moves)
                logging.info(f"Немедленно отправлено {len(manual_moves)} ручных движений")
            except Exception as e:
                logging.error(f"Ошибка отправки ручных движений: {e}")
    
    return {"ok": True, "ants": [ant.id for ant in ants]}

@app.post("/api/clear_manual_priority")
async def clear_manual_priority():
    """Очистка всей ручной приоритезации"""
    try:
        manual_priority_table.clear()
        logging.info("Ручная приоритезация очищена")
        return {"status": "success", "message": "Manual priority cleared"}
    except Exception as e:
        logging.error(f"Ошибка очистки ручной приоритезации: {e}")
        return {"status": "error", "message": str(e)}

# === Статические файлы для фронта ===
app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
