import React, { useState } from 'react';
import { HexMap_test } from './components/HexMap_test';

// --- Улучшенный парсер Python dict -> JSON ---
function pythonDictToJson(str: string): string {
  let s = str.trim();
  // Если строка начинается и заканчивается на кавычки — срезаем их
  if ((s.startsWith('"') && s.endsWith('"')) || (s.startsWith("'") && s.endsWith("'"))) {
    s = s.slice(1, -1);
  }
  // Удаляем переносы строк внутри объекта
  s = s.replace(/\n/g, ' ');
  // True/False/None -> true/false/null
  s = s.replace(/\bTrue\b/g, 'true').replace(/\bFalse\b/g, 'false').replace(/\bNone\b/g, 'null');
  // Одинарные кавычки -> двойные (но не внутри уже двойных)
  s = s.replace(/'/g, '"');
  // Ключи без кавычек -> с кавычками ("key":)
  s = s.replace(/([,{\[])(\s*)([a-zA-Z0-9_]+)(\s*):/g, '$1"$3":');
  // Иногда бывают запятые после последнего элемента в массиве/объекте — убираем
  s = s.replace(/,([ \t\r\n]*[}\]])/g, '$1');
  // Попытка починить вложенные объекты без кавычек
  // (очень грубо, но лучше чем ничего)
  s = s.replace(/([{,]\s*)([a-zA-Z0-9_]+)(\s*):/g, '$1"$2":');
  return s;
}

const TestArenaPage: React.FC = () => {
  const [arenaJson, setArenaJson] = useState('');
  const [submittedJson, setSubmittedJson] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [moves, setMoves] = useState<string>('// TODO: moves');
  const [afterJson, setAfterJson] = useState<string>('');

  const handleShow = async () => {
    let jsonStr = '';
    let parsed: any = null;
    try {
      jsonStr = pythonDictToJson(arenaJson);
      parsed = JSON.parse(jsonStr);
    } catch (e) {
      // Если не смогли — пробуем отправить на бэкенд для парсинга
      try {
        const resp = await fetch('http://localhost:8000/test/parse_dict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ raw: arenaJson })
        });
        if (!resp.ok) throw new Error('Backend parse error');
        parsed = await resp.json();
        jsonStr = JSON.stringify(parsed);
      } catch (e2: any) {
        setError('Ошибка парсинга/конвертации лога или запроса: ' + e2.message + '\n\nВставь кусок из backend.log целиком, не JSON!');
        setMoves('// TODO: moves');
        setAfterJson('');
        return;
      }
    }
    setSubmittedJson(jsonStr);
    setError(null);
    // Отправляем на backend
    try {
      const resp = await fetch('http://localhost:8000/test/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      if (!resp.ok) throw new Error('Ошибка запроса к backend');
      const data = await resp.json();
      setMoves(JSON.stringify(data.moves, null, 2));
      // --- Формируем afterJson: копируем исходный объект, подменяем ants на новые координаты ---
      if (parsed && parsed.ants && Array.isArray(parsed.ants)) {
        const antMap = Object.fromEntries((data.moves||[]).map((m: any) => [m.ant, m.path && m.path.length ? m.path[m.path.length-1] : null]));
        const newAnts = parsed.ants.map((ant: any) => {
          if (antMap[ant.id]) {
            return { ...ant, q: antMap[ant.id].q, r: antMap[ant.id].r };
          }
          return ant;
        });
        const afterObj = { ...parsed, ants: newAnts };
        setAfterJson(JSON.stringify(afterObj));
      } else {
        setAfterJson('');
      }
    } catch (e: any) {
      setError('Ошибка запроса к backend: ' + e.message);
      setMoves('// TODO: moves');
      setAfterJson('');
    }
  };

  return (
    <div style={{padding:32}}>
      <h2>Тест арены (вставь Python-словарь из backend.log, не JSON!)</h2>
      <textarea value={arenaJson} onChange={e => setArenaJson(e.target.value)} rows={10} cols={80} style={{fontFamily:'monospace',fontSize:14}}/>
      <div style={{margin:'12px 0'}}>
        <button onClick={handleShow} style={{fontSize:16,padding:'4px 16px'}}>Показать</button>
      </div>
      {error && <div style={{color:'red',marginBottom:8,whiteSpace:'pre-wrap'}}>{error}</div>}
      <div style={{margin:'24px 0'}}>
        {submittedJson && !error && <HexMap_test arenaJson={submittedJson} />}
      </div>
      <div>
        <h3>Moves (raw):</h3>
        <pre style={{background:'#eee',padding:8}}>{moves}</pre>
      </div>
      <div style={{margin:'32px 0'}}>
        {afterJson && !error && <>
          <h3>Карта после движения:</h3>
          <HexMap_test arenaJson={afterJson} />
        </>}
      </div>
    </div>
  );
};

export default TestArenaPage; 