import httpx
import asyncio
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

# === Конфигурация продакшн API ===
PROD_API_BASE = "https://games.datsteam.dev"
PROD_TOKEN = "5d48b42c-f41c-49c1-b83c-48cae5f52ea3"
TEAM_NAME = "SubSchool"

# === Модели данных ===
class RegisterRequest(BaseModel):
    name: str

class RegisterResponse(BaseModel):
    teamId: str
    home: List[Dict[str, int]]
    spot: Dict[str, int]

class MoveRequest(BaseModel):
    moves: List[Dict[str, Any]]

class ArenaResponse(BaseModel):
    ants: List[Dict[str, Any]]
    enemies: List[Dict[str, Any]]
    map: List[Dict[str, Any]]
    food: List[Dict[str, Any]]
    turnNo: int
    nextTurnIn: float
    home: List[Dict[str, int]]
    score: int
    spot: Dict[str, int]

# === API клиент ===
class GameAPI:
    def __init__(self):
        self.base_url = PROD_API_BASE
        self.token = PROD_TOKEN
        self.team_id: Optional[str] = None
        self.home: Optional[List[Dict[str, int]]] = None
        self.spot: Optional[Dict[str, int]] = None
        self.last_request_time = 0
        self.rps_limit = 3  # 3 запроса в секунду
        self.request_interval = 1.0 / self.rps_limit
        
    async def _rate_limit(self):
        """Соблюдение лимита 3 RPS"""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.request_interval:
            await asyncio.sleep(self.request_interval - time_since_last)
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Выполнение HTTP запроса с авторизацией"""
        await self._rate_limit()
        
        headers = {
            "X-Auth-Token": self.token,
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
    
    async def register(self) -> bool:
        """Регистрация команды"""
        try:
            # ВАЖНО: POST без тела, только заголовок X-Auth-Token
            await self._rate_limit()
            headers = {
                "X-Auth-Token": self.token,
                "accept": "application/json"
            }
            url = f"{self.base_url}/api/register"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                response_data = response.json()
                logging.info(f"REGISTER RESPONSE: {response_data}")
            self.team_id = response_data.get("teamId")
            self.home = response_data.get("home")
            self.spot = response_data.get("spot")
            logging.info(f"Зарегистрировались: teamId={self.team_id}, home={self.home}, spot={self.spot}")
            return True
        except httpx.HTTPStatusError as e:
            error_msg = str(e)
            try:
                error_data = e.response.json()
                logging.info(f"Ошибка регистрации: {error_data.get('message', error_msg)}")
            except:
                logging.error(f"HTTP ошибка регистрации: {e.response.status_code} - {error_msg}")
            # Не выходим, не возвращаем False, просто логируем
        except Exception as e:
            logging.error(f"Ошибка регистрации: {e}")
            # Не выходим, не возвращаем False, просто логируем
        return True  # Всегда возвращаем True, чтобы не отключать регистрацию
    
    async def get_arena(self) -> Optional[ArenaResponse]:
        """Получение состояния арены"""
        try:
            response_data = await self._make_request("GET", "/api/arena")
            return ArenaResponse(**response_data)
            
        except Exception as e:
            logging.error(f"Ошибка получения арены: {e}")
            return None
    
    async def send_moves(self, moves: List[Dict[str, Any]]) -> bool:
        """Отправка ходов"""
        try:
            # Отправляем массив ходов в обёртке {"moves": moves}
            logging.info(f"SENDING MOVES: {moves}")
            response_data = await self._make_request("POST", "/api/move", {"moves": moves})
            # Проверяем успешность
            if "error" in response_data:
                logging.error(f"MOVE ERROR: {response_data['error']}")
                return False
            else:
                logging.info(f"MOVE SUCCESS: {len(moves)} commands sent")
                return True
        except Exception as e:
            logging.error(f"Ошибка отправки ходов: {e}")
            return False
    
    async def get_logs(self) -> Optional[List[Dict]]:
        """Получение логов (для отладки)"""
        try:
            response_data = await self._make_request("GET", "/api/logs")
            return response_data
        except Exception as e:
            logging.error(f"Ошибка получения логов: {e}")
            return None

# === Глобальный экземпляр API ===
game_api = GameAPI()
