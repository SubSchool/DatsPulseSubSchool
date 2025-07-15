// === API клиент для фронта ===

const API_BASE = 'http://localhost:8000';

export interface GameStatus {
  is_running: boolean;
  team_id: string | null;
  score: number;
  turn_no: number;
  ants_count: number;
}

export interface GameState {
  ants: any[];
  enemies: any[];
  map: any[];
  food: any[];
  turnNo: number;
  nextTurnIn: number;
  home: any[];
  score: number;
  spot: any;
}

// === API функции ===

export async function getStatus(): Promise<GameStatus> {
  const response = await fetch(`${API_BASE}/api/status`);
  return response.json();
}

export async function startBot(): Promise<{status: string}> {
  const response = await fetch(`${API_BASE}/api/bot/start`, {
    method: 'POST',
  });
  return response.json();
}

export async function stopBot(): Promise<{status: string}> {
  const response = await fetch(`${API_BASE}/api/bot/stop`, {
    method: 'POST',
  });
  return response.json();
}

export async function getMap(): Promise<GameState> {
  const response = await fetch(`${API_BASE}/api/map`);
  return response.json();
}

export async function getArena(): Promise<GameState> {
  const response = await fetch(`${API_BASE}/api/arena`);
  return response.json();
}

export async function register(): Promise<{success: boolean, team_id: string}> {
  const response = await fetch(`${API_BASE}/api/register`, {
    method: 'POST',
  });
  return response.json();
}

export async function postManualPriority(source: {q:number, r:number}, target: {q:number, r:number}): Promise<any> {
  const response = await fetch(`${API_BASE}/api/manual_priority`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source, target })
  });
  return response.json();
}

// === WebSocket соединение ===

export function createWebSocket(): WebSocket {
  return new WebSocket(`ws://localhost:8000/ws`);
}

// === Периодическое обновление статуса ===

export function startStatusPolling(callback: (status: GameStatus) => void, interval: number = 1000) {
  const poll = async () => {
    try {
      const status = await getStatus();
      callback(status);
    } catch (error) {
      console.error('Error polling status:', error);
    }
  };
  
  poll(); // Сразу вызываем
  return setInterval(poll, interval);
}
