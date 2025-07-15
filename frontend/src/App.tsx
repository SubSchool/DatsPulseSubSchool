import { useState, useEffect, useCallback } from 'react';
import HexMap from './components/HexMap';
import ControlPanel from './components/ControlPanel';
import Sidebar from './components/Sidebar';
import { getStatus, createWebSocket, type GameState } from './utils/api';
import './App.css';

function App() {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  // === Инициализация WebSocket ===
  useEffect(() => {
    const websocket = createWebSocket();
    
    websocket.onopen = () => {
      addLog('WebSocket соединение установлено');
    };
    
    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setGameState(data);
      } catch (error) {
        addLog(`Ошибка парсинга WebSocket данных: ${error}`);
      }
    };
    
    websocket.onerror = (error) => {
      addLog(`WebSocket ошибка: ${error}`);
    };
    
    websocket.onclose = () => {
      addLog('WebSocket соединение закрыто');
    };
    
    return () => {
      websocket.close();
    };
  }, []);

  // === Периодическое обновление статуса ===
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        await getStatus();
      } catch (error) {
        console.error('Ошибка получения статуса:', error);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const addLog = useCallback((message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = `[${timestamp}] ${message}`;
    setLogs(prev => [...prev.slice(-99), logEntry]); // Храним последние 100 записей
  }, []);

  return (
    <div className="App">
      <div className="main-content">
        <div className="left-panel">
          <HexMap 
            map={gameState?.map || []}
            ants={gameState?.ants || []}
            enemies={gameState?.enemies || []}
            resources={gameState?.food || []}
          />
        </div>
        <div className="right-panel">
          <ControlPanel 
            mode="prod"
            setModeState={() => {}}
          />
          <div className="log-panel">
            <h3>Логи</h3>
            <div className="log-content">
              {logs.map((log, index) => (
                <div key={index} className="log-entry">{log}</div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <Sidebar 
        turn={gameState?.turnNo || 0}
        score={gameState?.score || 0}
        antsCount={gameState?.ants?.length || 0}
        log={logs}
      />
    </div>
  );
}

export default App;
