from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from .test_bot import test_make_moves
import ast

router = APIRouter()

@router.post('/move')
async def test_move(request: Request):
    arena = await request.json()
    moves = test_make_moves(arena)
    return JSONResponse(content={"moves": moves})

@router.post('/parse_dict')
async def parse_dict(request: Request):
    data = await request.body()
    try:
        # data — bytes, декодируем
        s = data.decode('utf-8')
        # Если пришёл JSON с ключом 'raw', берём его
        import json
        try:
            j = json.loads(s)
            if isinstance(j, dict) and 'raw' in j:
                s = j['raw']
        except Exception:
            pass
        # Парсим питоновский словарь
        obj = ast.literal_eval(s)
        return JSONResponse(content=obj)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400) 