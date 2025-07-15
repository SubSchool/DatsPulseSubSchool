from pydantic import BaseModel
from typing import List, Optional

class Ant(BaseModel):
    id: str
    type: int
    q: int
    r: int
    health: int
    food: Optional[dict] = None
    lastMove: Optional[List[dict]] = None
    move: Optional[List[dict]] = None
    lastAttack: Optional[dict] = None
    lastEnemyAnt: Optional[str] = None

class Enemy(BaseModel):
    id: Optional[str]
    type: int
    q: int
    r: int
    health: int
    food: Optional[dict] = None
    attack: Optional[int] = None

class Resource(BaseModel):
    q: int
    r: int
    type: int
    amount: int

class HexCell(BaseModel):
    q: int
    r: int
    type: int
    cost: int

class ArenaState(BaseModel):
    ants: List[Ant]
    enemies: List[Enemy]
    food: List[Resource]
    home: List[dict]
    map: List[HexCell]
    nextTurnIn: float
    score: int
    spot: dict
    turnNo: int

class MoveCmd(BaseModel):
    ant: str
    path: List[dict]  # [{'q': int, 'r': int}, ...]
