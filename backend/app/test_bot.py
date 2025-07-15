import networkx as nx
from collections import deque

# --- Константы по доке ---
SPEED = {0: 5, 1: 4, 2: 7}  # worker, fighter, scout
HEX_COST = {1: 1, 2: 1, 3: 2, 4: 1, 5: float('inf'), 0: 1}  # 0=unknown treated as empty

# --- BFS для поиска всех достижимых клеток с учётом ОП и cost ---
def reachable_cells(start, max_op, map_cells, occupied, allow_acid_pass=True):
    cell_map = {(c['q'], c['r']): c for c in map_cells}
    visited = {}
    queue = deque()
    queue.append((start, 0, []))
    while queue:
        pos, op_used, path = queue.popleft()
        if pos in visited and visited[pos] <= op_used:
            continue
        visited[pos] = op_used
        for dq, dr in [(-1,0),(1,0),(0,-1),(0,1),(-1,1),(1,-1)]:
            nq, nr = pos[0]+dq, pos[1]+dr
            if (nq, nr) not in cell_map:
                continue
            t = cell_map[(nq, nr)]['type']
            cost = cell_map[(nq, nr)].get('cost', HEX_COST.get(t, 1))
            if cost == float('inf') or (nq, nr) in occupied:
                continue
            next_op = op_used + cost
            if next_op > max_op:
                continue
            if t == 4 and allow_acid_pass:
                queue.append(((nq, nr), next_op, path+[(nq, nr)]))
            elif t != 4:
                queue.append(((nq, nr), next_op, path+[(nq, nr)]))
    return {pos for pos in visited if pos != start}

def shortest_path(start, goal, max_op, map_cells, occupied):
    cell_map = {(c['q'], c['r']): c for c in map_cells}
    queue = deque()
    queue.append((start, 0, []))
    visited = {}
    while queue:
        pos, op_used, path = queue.popleft()
        if pos == goal:
            return path + [pos]
        if pos in visited and visited[pos] <= op_used:
            continue
        visited[pos] = op_used
        for dq, dr in [(-1,0),(1,0),(0,-1),(0,1),(-1,1),(1,-1)]:
            nq, nr = pos[0]+dq, pos[1]+dr
            if (nq, nr) not in cell_map:
                continue
            t = cell_map[(nq, nr)]['type']
            cost = cell_map[(nq, nr)].get('cost', HEX_COST.get(t, 1))
            if cost == float('inf') or (nq, nr) in occupied:
                continue
            next_op = op_used + cost
            if next_op > max_op:
                continue
            if t == 4 and (nq, nr) == goal:
                continue
            queue.append(((nq, nr), next_op, path+[pos]))
    return None

def test_make_moves(arena):
    moves = []
    ants = arena['ants']
    map_cells = arena['map']
    food = arena.get('food', [])
    enemies = arena.get('enemies', [])
    home = set((h['q'], h['r']) for h in arena.get('home', []))
    spot = (arena['spot']['q'], arena['spot']['r']) if 'spot' in arena else None
    occupied = set((a['q'], a['r']) for a in ants)
    scout_positions = set((a['q'], a['r']) for a in ants if a['type']==2)
    unknowns = set((c['q'], c['r']) for c in map_cells if c['type']==0)
    food_cells = [(f['q'], f['r'], f['type'], f['amount']) for f in food]
    enemy_cells = set((e['q'], e['r']) for e in enemies)

    reserved_cells = set()  # Клетки, куда уже кто-то идёт
    reserved_food = set()   # Клетки с едой, которые уже выбраны

    for ant in ants:
        ant_id = ant['id']
        ant_type = ant['type']
        start = (ant['q'], ant['r'])
        max_op = SPEED.get(ant_type, 5)
        reach = reachable_cells(start, max_op, map_cells, occupied - {start} | reserved_cells)
        reach = {pos for pos in reach if map_cells[[ (c['q'],c['r']) for c in map_cells].index(pos)]['type'] != 4}
        # --- Если муравей несёт еду ---
        if ant.get('food') and ant['food'].get('amount',0) > 0:
            nest_targets = [pos for pos in reach if pos in home and pos not in reserved_cells]
            if nest_targets:
                target = min(nest_targets, key=lambda p: abs(p[0]-start[0])+abs(p[1]-start[1]))
                path = shortest_path(start, target, max_op, map_cells, occupied - {start} | reserved_cells)
                if path and len(path)>1:
                    moves.append({'ant': ant_id, 'path': [{'q':q,'r':r} for q,r in path[1:]]})
                    reserved_cells.add(path[1])
                    continue
        # --- Если есть еда в зоне досягаемости ---
        food_targets = [ (q,r,typ,amt) for (q,r,typ,amt) in food_cells if (q,r) in reach and (q,r) not in reserved_food and (q,r) not in reserved_cells ]
        if food_targets:
            if ant_type in (0,1):
                target = max(food_targets, key=lambda x: (x[3], -abs(x[0]-start[0])-abs(x[1]-start[1])))
                path = shortest_path(start, (target[0],target[1]), max_op, map_cells, occupied - {start} | reserved_cells)
                if path and len(path)>1:
                    moves.append({'ant': ant_id, 'path': [{'q':q,'r':r} for q,r in path[1:]]})
                    reserved_cells.add(path[1])
                    reserved_food.add((target[0],target[1]))
                    continue
        # --- Для бойца: если есть враг в зоне досягаемости ---
        if ant_type==1 and enemy_cells:
            enemy_targets = [pos for pos in reach if pos in enemy_cells and pos not in reserved_cells]
            if enemy_targets:
                target = min(enemy_targets, key=lambda p: abs(p[0]-start[0])+abs(p[1]-start[1]))
                path = shortest_path(start, target, max_op, map_cells, occupied - {start} | reserved_cells)
                if path and len(path)>1:
                    moves.append({'ant': ant_id, 'path': [{'q':q,'r':r} for q,r in path[1:]]})
                    reserved_cells.add(path[1])
                    continue
        # --- Для разведчика: ищем ближайшую неизвестную клетку, избегаем других разведчиков ---
        if ant_type==2 and unknowns:
            best = None
            best_score = -1e9
            for pos in reach:
                if pos in reserved_cells:
                    continue
                dist_to_unknown = min([abs(pos[0]-u[0])+abs(pos[1]-u[1]) for u in unknowns], default=1000)
                dist_to_scout = min([abs(pos[0]-s[0])+abs(pos[1]-s[1]) for s in scout_positions if s!=start], default=1000)
                score = -dist_to_unknown + dist_to_scout
                if score > best_score:
                    best = pos
                    best_score = score
            if best:
                path = shortest_path(start, best, max_op, map_cells, occupied - {start} | reserved_cells)
                if path and len(path)>1:
                    moves.append({'ant': ant_id, 'path': [{'q':q,'r':r} for q,r in path[1:]]})
                    reserved_cells.add(path[1])
                    continue
        # --- Если нет целей — идём в самую дальнюю достижимую точку ---
        free_reach = [pos for pos in reach if pos not in reserved_cells]
        if free_reach:
            dists = [(abs(pos[0]-start[0])+abs(pos[1]-start[1]), pos) for pos in free_reach]
            max_dist = max(dists)[0]
            farthest = [pos for dist,pos in dists if dist==max_dist]
            import random
            target = random.choice(farthest)
            path = shortest_path(start, target, max_op, map_cells, occupied - {start} | reserved_cells)
            if path and len(path)>1:
                moves.append({'ant': ant_id, 'path': [{'q':q,'r':r} for q,r in path[1:]]})
                reserved_cells.add(path[1])
                continue
    return moves 