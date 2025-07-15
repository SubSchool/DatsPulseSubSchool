import asyncio
import logging
import random
from typing import Dict, List, Optional, Tuple, Set
from .api import game_api
from .models import ArenaState, Ant, HexCell, Resource, Enemy, MoveCmd

# === Настройка логирования ===
logging.basicConfig(
    level=logging.INFO,
    format='[LOG] %(message)s',
    handlers=[
        logging.FileHandler('backend.log'),
        logging.StreamHandler()
    ]
)

class AntBot:
    def __init__(self):
        self.known_map: Dict[Tuple[int, int], Dict] = {}
        self.state: Optional[ArenaState] = None
        self.websockets: List = []
        self._last_positions: Dict[str, Tuple[int, int]] = {}
        self._stuck_counters: Dict[str, int] = {}
        self._last_spawned_home_cell: Dict[str, Tuple[int, int]] = {}
        self._log_count = 0
        self.is_running = False
        self._arena_task = None
        self._move_task = None
        self._register_task = None
        self._periodic_register_task = None
        self.manual_priority_table: List[Dict] = []  # Таблица ручной приоритезации

    async def start(self):
        """Запуск бота"""
        self.is_running = True
        logging.info("Бот запущен")
        # Параллельно: регистрация, арена, движения
        self._register_task = asyncio.create_task(self._register_loop())
        self._arena_task = asyncio.create_task(self._arena_loop())
        self._move_task = asyncio.create_task(self._move_loop())
        self._periodic_register_task = asyncio.create_task(self._periodic_register())

    async def _register_loop(self):
        """Постоянно пытаемся зарегистрироваться"""
        while self.is_running:
            try:
                await game_api.register()
            except Exception as e:
                logging.error(f"Ошибка регистрации: {e}")
            await asyncio.sleep(30)

    async def _periodic_register(self):
        """Периодическая перерегистрация каждые 5 минут"""
        while self.is_running:
            await asyncio.sleep(300)
            try:
                await game_api.register()
            except Exception as e:
                logging.error(f"Ошибка перерегистрации: {e}")

    async def _arena_loop(self):
        """Постоянно получаем арену"""
        while self.is_running:
            try:
                arena_data = await game_api.get_arena()
                if arena_data:
                    # Обновляем известную карту
                    for cell in arena_data.map:
                        key = (cell['q'], cell['r'])
                        self.known_map[key] = cell.copy()
                    # Создаем состояние
                    self.state = ArenaState(
                        ants=[Ant(**ant) for ant in arena_data.ants],
                        enemies=[Enemy(**enemy) for enemy in arena_data.enemies],
                        map=[HexCell(**cell) for cell in arena_data.map],
                        food=[Resource(**food) for food in arena_data.food],
                        turnNo=arena_data.turnNo,
                        nextTurnIn=arena_data.nextTurnIn,
                        home=arena_data.home,  # Оставляем как есть (list of dict)
                        score=arena_data.score,
                        spot=arena_data.spot   # Оставляем как есть (dict)
                    )
                    await self.push_state()
            except Exception as e:
                logging.error(f"Ошибка получения арены: {e}")
            await asyncio.sleep(1)

    async def _move_loop(self):
        """Постоянно отправляем движения"""
        while self.is_running:
            try:
                # УБРАНО: Проверка регистрации
              #   if not game_api.team_id:
               #       logging.info("Не зарегистрированы в игре, пропускаем отправку ходов")
             #         await asyncio.sleep(1)
              #        continue
                
                if self.state and self.state.ants:
                    logging.info(f"ANTS: {self.state.ants}")
                    moves = await self.make_moves()
                    logging.info(f"MOVES: {moves}")
                    if moves:  # Отправляем только если есть ходы
                        await game_api.send_moves(moves)
                        logging.info("SEND_MOVES called")
            except Exception as e:
                logging.error(f"Ошибка отправки движений: {e}")
            await asyncio.sleep(1)

    async def make_moves(self) -> List[dict]:
        """Генерация ходов для всех муравьев (улучшено)"""
        if not self.state or not self.state.ants:
            return []
        self._update_manual_priority_status()
        moves = []
        ants = [ant.dict() if hasattr(ant, 'dict') else dict(ant) for ant in self.state.ants]
        map_cells = [cell.dict() if hasattr(cell, 'dict') else dict(cell) for cell in self.state.map]
        food = [f.dict() if hasattr(f, 'dict') else dict(f) for f in self.state.food]
        enemies = [e.dict() if hasattr(e, 'dict') else dict(e) for e in self.state.enemies]
        home_cells = [h if isinstance(h, dict) else h.dict() for h in self.state.home]
        map_dict = {(cell['q'], cell['r']): cell for cell in map_cells}
        food_dict = {(f['q'], f['r']): f for f in food}
        ant_positions = {(ant['q'], ant['r']): ant for ant in ants}
        home_positions = {(h['q'], h['r']) for h in home_cells}
        for ant in ants:
            ant_id = ant['id']
            current_pos = (ant['q'], ant['r'])
            ant_type = ant['type']
            food_amount = ant['food']['amount']
            # === Проверяем ручную приоритезацию ===
            manual_move = self._check_manual_priority(ant_id, current_pos, ant_positions, map_dict, home_positions)
            if manual_move:
                moves.append(manual_move)
                continue
            # === Если муравей несёт еду — идём к home ===
            if food_amount > 0:
                move = self._move_to_home(ant_id, current_pos, ant_positions, map_dict, home_positions)
                if move:
                    moves.append(move)
                    continue
                # Если не получилось — fallback к home
                fallback = self._fallback_move(ant_id, current_pos, ant_positions, map_dict, home_positions, has_food=True)
                if fallback:
                    moves.append(fallback)
                    continue
            # === Для рабочих и бойцов — ищем еду или врагов ===
            if ant_type in (0, 1):
                # Ищем еду
                food_targets = [pos for pos, f in food_dict.items() if f['amount'] > 0]
                if food_targets:
                    # Ближайшая еда
                    target = min(food_targets, key=lambda pos: self._distance(current_pos, pos))
                    path = self._find_path(current_pos, target, ant_positions, map_dict, home_positions)
                    if path:
                        moves.append({'ant': ant_id, 'path': path})
                        continue
                # Для бойца — ищем врага
                if ant_type == 1 and enemies:
                    enemy_targets = [(e['q'], e['r']) for e in enemies]
                    if enemy_targets:
                        target = min(enemy_targets, key=lambda pos: self._distance(current_pos, pos))
                        path = self._find_path(current_pos, target, ant_positions, map_dict, home_positions)
                        if path:
                            moves.append({'ant': ant_id, 'path': path})
                            continue
            # === Для разведчика — ищем неизвестные клетки ===
            if ant_type == 2:
                unknown_cells = [pos for pos, cell in map_dict.items() if cell['type'] == 0]
                if unknown_cells:
                    target = min(unknown_cells, key=lambda pos: self._distance(current_pos, pos))
                    path = self._find_path(current_pos, target, ant_positions, map_dict, home_positions)
                    if path:
                        moves.append({'ant': ant_id, 'path': path})
                        continue
            # === Если ничего не подошло — fallback ===
            fallback = self._fallback_move(ant_id, current_pos, ant_positions, map_dict, home_positions, has_food=(food_amount > 0))
            if fallback:
                moves.append(fallback)
        logging.info(f"Сформировано {len(moves)} валидных команд движения")
        for move in moves:
            path_str = " -> ".join([f"({step['q']},{step['r']})" for step in move['path']])
            logging.info(f"   {move['ant']}: {path_str}")
        return moves
    def _generate_move(self, ant: dict, ant_positions: dict, map_dict: dict, food_dict: dict, home_positions: set, enemies: list) -> dict:
        ant_id = ant['id']
        current_pos = (ant['q'], ant['r'])
        ant_type = ant['type']
        food_amount = ant['food']['amount']
        if food_amount > 0:
            return self._move_to_home(ant_id, current_pos, ant_positions, map_dict, home_positions)
        if ant_type == 0:
            return self._worker_strategy(ant_id, current_pos, ant_positions, map_dict, food_dict, home_positions)
        elif ant_type == 1:
            return self._scout_strategy(ant_id, current_pos, ant_positions, map_dict, home_positions)
        elif ant_type == 2:
            return self._fighter_strategy(ant_id, current_pos, ant_positions, map_dict, home_positions, enemies)
        return None
    def _worker_strategy(self, ant_id: str, current_pos: tuple, ant_positions: dict, map_dict: dict, food_dict: dict, home_positions: set) -> dict:
        # === Сначала ищем еду ===
        for food_pos, food_data in food_dict.items():
            if food_data['amount'] > 0:
                path = self._find_path(current_pos, food_pos, ant_positions, map_dict, home_positions)
                if path:
                    logging.info(f"Worker {ant_id}: идём за едой к {food_pos}")
                    return {'ant': ant_id, 'path': path}
        
        # === Если еды нет, идём подальше от муравейника ===
        return self._explore_away_from_home(ant_id, current_pos, ant_positions, map_dict, home_positions)
    def _scout_strategy(self, ant_id: str, current_pos: tuple, ant_positions: dict, map_dict: dict, home_positions: set) -> dict:
        # === Сначала ищем неизвестные клетки ===
        unknown_cell = self._find_unknown_cell(current_pos, map_dict, ant_positions)
        if unknown_cell:
            path = self._find_path(current_pos, unknown_cell, ant_positions, map_dict, home_positions)
            if path:
                logging.info(f"Scout {ant_id}: исследуем неизвестную клетку {unknown_cell}")
                return {'ant': ant_id, 'path': path}
        
        # === Если неизвестных клеток нет, идём подальше от муравейника ===
        return self._explore_away_from_home(ant_id, current_pos, ant_positions, map_dict, home_positions)
    def _fighter_strategy(self, ant_id: str, current_pos: tuple, ant_positions: dict, map_dict: dict, home_positions: set, enemies: list) -> dict:
        # === Сначала ищем врагов поблизости ===
        for enemy in enemies:
            enemy_pos = (enemy['q'], enemy['r'])
            if self._distance(current_pos, enemy_pos) <= 3:  # Увеличиваем радиус атаки
                path = self._find_path(current_pos, enemy_pos, ant_positions, map_dict, home_positions)
                if path:
                    logging.info(f"Fighter {ant_id}: атакуем врага в {enemy_pos}")
                    return {'ant': ant_id, 'path': path}
        
        # === Если врагов нет, патрулируем вокруг базы ===
        patrol_move = self._patrol_around_spot(ant_id, current_pos, ant_positions, map_dict, home_positions)
        if patrol_move:
            logging.info(f"Fighter {ant_id}: патрулируем вокруг базы")
            return patrol_move
        
        # === Fallback - исследуем вдали от базы ===
        return self._explore_away_from_home(ant_id, current_pos, ant_positions, map_dict, home_positions)
    def _move_to_home(self, ant_id: str, current_pos: tuple, ant_positions: dict, map_dict: dict, home_positions: set) -> dict:
        for home_pos in home_positions:
            if home_pos not in ant_positions:
                path = self._find_path(current_pos, home_pos, ant_positions, map_dict, home_positions)
                if path:
                    return {'ant': ant_id, 'path': path}
        closest_home = min(home_positions, key=lambda pos: self._distance(current_pos, pos))
        path = self._find_path(current_pos, closest_home, ant_positions, map_dict, home_positions)
        if path:
            return {'ant': ant_id, 'path': path}
        return None
    def _move_to_spot(self, ant_id: str, current_pos: tuple, ant_positions: dict, map_dict: dict) -> dict:
        spot_pos = (self.state.spot.q, self.state.spot.r)
        path = self._find_path(current_pos, spot_pos, ant_positions, map_dict, set())
        if path:
            return {'ant': ant_id, 'path': path}
        return None
    
    def _explore_away_from_home(self, ant_id: str, current_pos: tuple, ant_positions: dict, map_dict: dict, home_positions: set) -> dict:
        """Исследование вдали от муравейника"""
        if not home_positions:
            return self._random_move(ant_id, current_pos, ant_positions, map_dict, home_positions)
        
        # Находим центр муравейника
        home_center = self._get_home_center(home_positions)
        
        # Вычисляем направление от муравейника
        direction_from_home = self._get_direction_from_home(current_pos, home_center)
        
        # Ищем цель в этом направлении на расстоянии 5-10 клеток
        target_pos = self._find_exploration_target(current_pos, direction_from_home, ant_positions, map_dict, home_positions)
        
        if target_pos:
            path = self._find_path(current_pos, target_pos, ant_positions, map_dict, home_positions)
            if path:
                logging.info(f"Worker {ant_id}: исследуем в направлении {direction_from_home} к {target_pos}")
                return {'ant': ant_id, 'path': path}
        
        # Fallback - случайное движение
        return self._random_move(ant_id, current_pos, ant_positions, map_dict, home_positions)
    def _patrol_around_spot(self, ant_id: str, current_pos: tuple, ant_positions: dict, map_dict: dict, home_positions: set) -> dict:
        # Исправлено: spot_pos теперь всегда tuple
        spot = self.state.spot
        if isinstance(spot, dict):
            spot_pos = (spot['q'], spot['r'])
        else:
            spot_pos = (spot.q, spot.r)
        for dq in range(-2, 3):
            for dr in range(-2, 3):
                if abs(dq) + abs(dr) <= 2:
                    patrol_pos = (spot_pos[0] + dq, spot_pos[1] + dr)
                    if (patrol_pos not in ant_positions and patrol_pos in map_dict and map_dict[patrol_pos]['type'] != 5):
                        path = self._find_path(current_pos, patrol_pos, ant_positions, map_dict, home_positions)
                        if path:
                            return {'ant': ant_id, 'path': path}
        return None
    def _find_path(self, start: Tuple[int, int], goal: Tuple[int, int], ant_positions: Dict,
                  map_dict: Dict, home_positions: Set) -> Optional[List[Dict[str, int]]]:
        """Поиск пути A*"""
        if start == goal:
            return []
        
        # Простой поиск в ширину для соседних клеток
        directions = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]
        
        for dq, dr in directions:
            new_pos = (start[0] + dq, start[1] + dr)
            if (new_pos == goal and 
                new_pos not in ant_positions and 
                new_pos in map_dict and 
                map_dict[new_pos]['type'] != 5):
                return [{'q': new_pos[0], 'r': new_pos[1]}]
        
        return None
    
    def _random_move(self, ant_id: str, current_pos: Tuple[int, int], ant_positions: Dict,
                    map_dict: Dict, home_positions: Set, has_food: bool = False) -> Optional[dict]:
        """
        Улучшенный fallback: выбираем не просто случайного соседа,
        а из трёх, которые ближе (если с едой) или дальше (если без еды) от home.
        """
        directions = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]
        candidates = []
        for dq, dr in directions:
            new_pos = (current_pos[0] + dq, current_pos[1] + dr)
            if (new_pos not in ant_positions and 
                new_pos in map_dict and 
                map_dict[new_pos]['type'] != 5):
                candidates.append(new_pos)
        if not candidates:
            return None
        # Если нет home — просто случайный
        if not home_positions:
            target = random.choice(candidates)
            return {'ant': ant_id, 'path': [{'q': target[0], 'r': target[1]}]}
        # Вычисляем расстояния до home
        home_center = self._get_home_center(home_positions)
        dists = [(pos, self._distance(pos, home_center)) for pos in candidates]
        # Для с едой — ближе к home, для без еды — дальше
        if has_food:
            dists.sort(key=lambda x: x[1])  # ближе
        else:
            dists.sort(key=lambda x: -x[1]) # дальше
        top3 = [pos for pos, _ in dists[:3]] if len(dists) >= 3 else [pos for pos, _ in dists]
        target = random.choice(top3)
        return {'ant': ant_id, 'path': [{'q': target[0], 'r': target[1]}]}

    def _fallback_move(self, ant_id: str, current_pos: Tuple[int, int], ant_positions: Dict,
                      map_dict: Dict, home_positions: Set, has_food: bool = False) -> Optional[dict]:
        """
        Улучшенный fallback: делегирует на _random_move с учётом еды.
        """
        move = self._random_move(ant_id, current_pos, ant_positions, map_dict, home_positions, has_food)
        if move:
            logging.info(f"Fallback для муравья {ant_id}: улучшенный random, выбрана клетка {move['path'][0]}")
        return move
    
    def _distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        """Расстояние между двумя позициями"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    
    def _get_home_center(self, home_positions: set) -> Tuple[int, int]:
        """Вычисляем центр муравейника"""
        if not home_positions:
            return (0, 0)
        
        total_q = sum(pos[0] for pos in home_positions)
        total_r = sum(pos[1] for pos in home_positions)
        count = len(home_positions)
        
        return (total_q // count, total_r // count)
    
    def _get_direction_from_home(self, current_pos: Tuple[int, int], home_center: Tuple[int, int]) -> Tuple[int, int]:
        """Вычисляем направление от муравейника"""
        dq = current_pos[0] - home_center[0]
        dr = current_pos[1] - home_center[1]
        
        # Нормализуем направление
        if dq != 0:
            dq = dq // abs(dq)
        if dr != 0:
            dr = dr // abs(dr)
        
        return (dq, dr)
    
    def _find_exploration_target(self, current_pos: Tuple[int, int], direction: Tuple[int, int], 
                                ant_positions: dict, map_dict: dict, home_positions: set) -> Optional[Tuple[int, int]]:
        """Ищем цель для исследования в заданном направлении"""
        # Пробуем разные расстояния от 5 до 10 клеток
        for distance in range(5, 11):
            target_q = current_pos[0] + direction[0] * distance
            target_r = current_pos[1] + direction[1] * distance
            target_pos = (target_q, target_r)
            
            # Проверяем что клетка доступна
            if (target_pos not in ant_positions and 
                target_pos in map_dict and 
                map_dict[target_pos]['type'] != 5):  # Не стена
                return target_pos
        
        # Если не нашли в этом направлении, пробуем соседние направления
        directions = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]
        for dq, dr in directions:
            for distance in range(3, 8):
                target_q = current_pos[0] + dq * distance
                target_r = current_pos[1] + dr * distance
                target_pos = (target_q, target_r)
                
                if (target_pos not in ant_positions and 
                    target_pos in map_dict and 
                    map_dict[target_pos]['type'] != 5):
                    return target_pos
        
        return None
    
    async def push_state(self):
        """Отправка состояния на фронт"""
        if not self.state:
            return
        
        state_data = self.state.model_dump()
        
        for ws in self.websockets:
            try:
                await ws.send_json(state_data)
            except Exception:
                pass
    
    def stop(self):
        self.is_running = False
        logging.info("Бот остановлен")
        # Останавливаем все задачи
        for task in [self._register_task, self._arena_task, self._move_task, self._periodic_register_task]:
            if task:
                task.cancel()

    def _find_unknown_cell(self, current_pos, map_dict, ant_positions):
        # directions for hex grid
        directions = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]
        # BFS по всей карте, ищем ближайший неизвестный гекс
        visited = set()
        queue = [current_pos]
        while queue:
            pos = queue.pop(0)
            if pos not in map_dict and pos not in ant_positions:
                return pos
            visited.add(pos)
            for dq, dr in directions:
                next_pos = (pos[0] + dq, pos[1] + dr)
                if next_pos not in visited and next_pos not in queue:
                    queue.append(next_pos)
        return None

    def _update_manual_priority_status(self):
        """Обновляем статусы в таблице ручной приоритезации"""
        if not self.state or not self.manual_priority_table:
            return
        
        for entry in self.manual_priority_table:
            if entry['status']:  # Уже выполнено
                continue
            
            # Ищем муравья
            ant = next((ant for ant in self.state.ants if ant.id == entry['ant_id']), None)
            if not ant:
                continue
            
            # Проверяем, дошёл ли до цели
            # Исправлено: поддержка dict и pydantic
            q = ant['q'] if isinstance(ant, dict) else ant.q
            r = ant['r'] if isinstance(ant, dict) else ant.r
            if q == entry['target_q'] and r == entry['target_r']:
                entry['status'] = True
                logging.info(f"Муравей {entry['ant_id']} достиг ручной цели ({entry['target_q']}, {entry['target_r']})")
    
    def _check_manual_priority(self, ant_id: str, current_pos: tuple, ant_positions: dict, map_dict: dict, home_positions: set) -> Optional[dict]:
        """Проверяем ручную приоритезацию для муравья"""
        if not self.manual_priority_table:
            return None
        
        # Ищем активную цель для этого муравья
        for entry in self.manual_priority_table:
            if entry['ant_id'] == ant_id and not entry['status']:
                target_pos = (entry['target_q'], entry['target_r'])
                path = self._find_path(current_pos, target_pos, ant_positions, map_dict, home_positions)
                if path:
                    logging.info(f"Ручная приоритезация для муравья {ant_id}: идём к ({entry['target_q']}, {entry['target_r']})")
                    return {'ant': ant_id, 'path': path}
        
        return None

# === Экспортируем глобальный экземпляр бота ===
bot_manager = AntBot()  # Глобальный бот для FastAPI
