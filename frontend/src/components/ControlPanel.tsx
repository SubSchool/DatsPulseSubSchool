import React from 'react';
import { startBot, stopBot, getMap } from '../utils/api';

interface Props {
  mode: string;
  setModeState: (mode: string) => void;
}

const ControlPanel: React.FC<Props> = ({ mode }) => {
  const handleStart = async () => {
    try {
      await startBot();
      console.log('Бот запущен');
    } catch (error) {
      console.error('Ошибка запуска бота:', error);
    }
  };

  const handleStop = async () => {
    try {
      await stopBot();
      console.log('Бот остановлен');
    } catch (error) {
      console.error('Ошибка остановки бота:', error);
    }
  };

  const handleRefresh = async () => {
    try {
      await getMap();
      console.log('Карта обновлена');
    } catch (error) {
      console.error('Ошибка обновления карты:', error);
    }
  };

  return (
    <div className="control-panel">
      <h3>Управление</h3>
      <div className="controls">
        <button onClick={handleStart} className="btn btn-start">
          Запустить бота
        </button>
        <button onClick={handleStop} className="btn btn-stop">
          Остановить бота
        </button>
        <button onClick={handleRefresh} className="btn btn-refresh">
          Обновить карту
        </button>
      </div>
      <div className="mode-info">
        <p>Режим: <strong>{mode}</strong></p>
        <p>API: <strong>games.datsteam.dev</strong></p>
      </div>
    </div>
  );
};

export default ControlPanel;
