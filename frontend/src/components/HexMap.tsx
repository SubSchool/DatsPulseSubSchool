import React, { useState } from 'react';
import { postManualPriority } from '../utils/api';

// --- Интерфейсы ---
interface Hex { q: number; r: number; type: string; _color?: string; cost?: number; }
interface Ant { id: string; q: number; r: number; type: string | number; hp?: number; food?: any; }
interface Enemy { id: string; q: number; r: number; type: string | number; hp?: number; }
interface Resource { q: number; r: number; type: string | number; amount: number; }
interface Props { map: Hex[]; ants: Ant[]; enemies: Enemy[]; resources: Resource[]; }

// --- Константы визуализации ---
const HEX_SIZE = 24;
const SQRT3 = Math.sqrt(3);
const PADDING = 32;
const COORD_OFFSET = 32;
const BOTTOM_PADDING = 56;

// --- Маппинг типов клеток ---
const TYPE_MAP: Record<string | number, {name: string, color: string}> = {
  1: { name: 'nest', color: '#ffe066' },
  2: { name: 'empty', color: '#e0e0e0' },
  3: { name: 'mud', color: '#a67c52' },
  4: { name: 'acid', color: '#e57373' },
  5: { name: 'rock', color: '#555' },
  0: { name: 'unknown', color: '#ccc' },
  'nest': { name: 'nest', color: '#ffe066' },
  'empty': { name: 'empty', color: '#e0e0e0' },
  'mud': { name: 'mud', color: '#a67c52' },
  'acid': { name: 'acid', color: '#e57373' },
  'rock': { name: 'rock', color: '#555' },
  'unknown': { name: 'unknown', color: '#ccc' },
};

// --- Маппинг ресурсов ---
const RESOURCE_TYPE_MAP: Record<string | number, {name: string, color: string, icon: (props?: any) => React.ReactNode}> = {
  1: {
    name: 'Яблоко (apple)',
    color: '#e53935',
    icon: (props = {}) => <circle cx={11} cy={11} r={7} fill="#e53935" stroke="#b71c1c" strokeWidth={2} {...props}/>
  },
  2: {
    name: 'Хлеб (bread)',
    color: '#ffe082',
    icon: (props = {}) => <rect x={5} y={8} width={12} height={7} rx={2} fill="#ffe082" stroke="#bfa040" strokeWidth={2} {...props}/>
  },
  3: {
    name: 'Нектар (nectar)',
    color: '#8e24aa',
    icon: (props = {}) => <ellipse cx={11} cy={13} rx={6} ry={8} fill="#8e24aa" stroke="#4a148c" strokeWidth={2} {...props}/>
  },
  'apple': {
    name: 'Яблоко (apple)',
    color: '#e53935',
    icon: (props = {}) => <circle cx={11} cy={11} r={7} fill="#e53935" stroke="#b71c1c" strokeWidth={2} {...props}/>
  },
  'bread': {
    name: 'Хлеб (bread)',
    color: '#ffe082',
    icon: (props = {}) => <rect x={5} y={8} width={12} height={7} rx={2} fill="#ffe082" stroke="#bfa040" strokeWidth={2} {...props}/>
  },
  'nectar': {
    name: 'Нектар (nectar)',
    color: '#8e24aa',
    icon: (props = {}) => <ellipse cx={11} cy={13} rx={6} ry={8} fill="#8e24aa" stroke="#4a148c" strokeWidth={2} {...props}/>
  },
};

const LegendHex: React.FC<{color:string,label:string}> = ({color,label}) => (
  <span style={{display:'inline-flex',alignItems:'center',marginRight:12}}>
    <svg width={22} height={22} style={{marginRight:4}}>
      <polygon points={getHexPoints(11,11,10)} fill={color} stroke="#888" strokeWidth={1}/>
    </svg>
    {label}
  </span>
);

const ResourceLegend: React.FC<{type: string | number}> = ({type}) => {
  const res = RESOURCE_TYPE_MAP[String(type)];
  return (
    <span style={{display:'inline-flex',alignItems:'center',marginRight:12}}>
      <svg width={22} height={22} style={{marginRight:4}}>{res.icon()}</svg>
      {res.name}
    </span>
  );
};

function getHexPoints(x: number, y: number, size: number) {
  const points = [];
  for (let i = 0; i < 6; i++) {
    const angle = Math.PI / 3 * i + Math.PI / 6;
    points.push([
      x + size * Math.cos(angle),
      y + size * Math.sin(angle)
    ]);
  }
  return points.map(p => p.join(",")).join(" ");
}

const HexMap: React.FC<Props> = ({ map, ants, enemies, resources }) => {
  const [selectedHexes, setSelectedHexes] = useState<{q:number, r:number}[]>([]);
  console.log('HexMap props:', { map, ants, enemies, resources });
  console.log('HexMap map:', map);
  // --- Жёсткая защита: если что-то не массив — подставляем [] ---
  const safeMap = Array.isArray(map) ? map : [];
  const safeAnts = Array.isArray(ants) ? ants : [];
  const safeEnemies = Array.isArray(enemies) ? enemies : [];
  const safeResources = Array.isArray(resources) ? resources : [];

  // --- Если карта пуста, не рендерим SVG ---
  if (!safeMap.length) {
    return <div style={{color: 'red', textAlign: 'center', padding: 40}}>Нет карты для отображения</div>;
  }
  // --- Жёстко приводим все координаты и cost к числам ---
  const mappedMap = safeMap.map(cell => {
    let t = String(cell.type);
    const info = TYPE_MAP[t] || TYPE_MAP[0];
    // --- Проверяем наличие cost, если нет — не добавляем ---
    const base = {
      ...cell,
      q: Number(cell.q),
      r: Number(cell.r),
      type: info.name,
      _color: info.color
    };
    return cell.cost !== undefined ? { ...base, cost: Number(cell.cost) } : base;
  });
  const mappedAnts = safeAnts.map(ant => ({
    ...ant,
    q: Number(ant.q),
    r: Number(ant.r),
    type: typeof ant.type === 'string' && !isNaN(Number(ant.type)) ? Number(ant.type) : ant.type
  }));
  const mappedEnemies = safeEnemies.map(e => ({
    ...e,
    q: Number(e.q),
    r: Number(e.r),
    type: typeof e.type === 'string' && !isNaN(Number(e.type)) ? Number(e.type) : e.type
  }));
  const mappedResources = safeResources.map(res => ({
    ...res,
    q: Number(res.q),
    r: Number(res.r),
    type: typeof res.type === 'string' && !isNaN(Number(res.type)) ? Number(res.type) : res.type,
    amount: Number(res.amount)
  }));
  // --- Координатные границы ---
  const qs = mappedMap.map(h => h.q);
  const rs = mappedMap.map(h => h.r);
  const minQ = Math.min(...qs);
  const maxQ = Math.max(...qs);
  const minR = Math.min(...rs);
  const maxR = Math.max(...rs);
  const PAD = 1;
  // --- Прямоугольная сетка для hex-ов ---
  const fullHexes: Record<string, Hex> = {};
  mappedMap.forEach(h => { fullHexes[`${h.q},${h.r}`] = h; });
  const rectMap: Hex[] = [];
  for (let r = minR - PAD; r <= maxR + PAD; r++) {
    for (let q = minQ - PAD; q <= maxQ + PAD; q++) {
      const key = `${q},${r}`;
      if (fullHexes[key]) {
        rectMap.push(fullHexes[key]);
      } else {
        rectMap.push({ q, r, type: 'unknown', _color: TYPE_MAP[0].color });
      }
    }
  }
  // --- Плотная axial-гекс сетка ---
  const hexToPixel = (q: number, r: number) => {
    const x = PADDING + COORD_OFFSET + HEX_SIZE * SQRT3 * (q - minQ + PAD + (r - minR + PAD) / 2);
    const y = PADDING + COORD_OFFSET + HEX_SIZE * 3/2 * (r - minR + PAD);
    return { x, y };
  };
  // --- Для координат ---
  const allQ = [];
  for (let q = minQ - PAD; q <= maxQ + PAD; q++) allQ.push(q);
  const allR = [];
  for (let r = minR - PAD; r <= maxR + PAD; r++) allR.push(r);
  // --- Для верхней косой линии (верхний край hex-поля) ---
  const topEdge: {q: number, r: number, x: number, y: number}[] = [];
  for (let q of allQ) {
    let minRforQ = null;
    for (let r = minR - PAD; r <= maxR + PAD; r++) {
      if (rectMap.find(h => h.q === q && h.r === r)) {
        minRforQ = r;
        break;
      }
    }
    if (minRforQ !== null) {
      const {x, y} = hexToPixel(q, minRforQ);
      topEdge.push({q, r: minRforQ, x, y});
    }
  }
  // --- Размер SVG ---
  const width = PADDING + COORD_OFFSET + HEX_SIZE * SQRT3 * (maxQ - minQ + 3 + (maxR - minR + 3)/2) + PADDING;
  const height = PADDING + COORD_OFFSET + HEX_SIZE * 3/2 * (maxR - minR + 3) + PADDING + BOTTOM_PADDING;

  // --- Обработчик клика по гексу ---
  const handleHexClick = async (hex: {q:number, r:number}) => {
    const idx = selectedHexes.findIndex(h => h.q === hex.q && h.r === hex.r);
    let newSelected;
    if (idx !== -1) {
      // Уже выделен — снять выделение
      newSelected = selectedHexes.filter((_, i) => i !== idx);
    } else {
      // Добавить в конец
      newSelected = [...selectedHexes, {q: hex.q, r: hex.r}];
      if (newSelected.length > 2) newSelected = newSelected.slice(-2);
    }
    setSelectedHexes(newSelected);
    // Если выбрано два — отправить и сбросить
    if (newSelected.length === 2) {
      await postManualPriority(newSelected[0], newSelected[1]);
      setTimeout(() => setSelectedHexes([]), 200); // сбросить выделение
    }
  };

  return (
    <div style={{
      width: '100%',
      minWidth: 600,
      minHeight: 500,
      maxWidth: '100vw',
      maxHeight: '70vh',
      overflow: 'auto',
      position: 'relative',
      background: '#f5f5f5',
      border: '1px solid #aaa',
      margin: '0 auto',
      boxSizing: 'border-box',
    }}>
      <svg width={width} height={height+28} style={{ display: 'block', margin: '0 auto', background: '#eee', border: '1px solid #aaa' }}>
        {/* --- Диагональная линия через центры верхних hex-ов --- */}
        <polyline
          points={topEdge.map(({x, y}) => `${x},${y}`).join(' ')}
          fill="none"
          stroke="#1976d2"
          strokeWidth={2}
          opacity={0.25}
        />
        {/* --- Цветные hex-и --- */}
        {rectMap.map((hex, i) => {
          const { x, y } = hexToPixel(hex.q, hex.r);
          const fill = hex._color || '#eee';
          const isSelected = selectedHexes.findIndex(h => h.q === hex.q && h.r === hex.r) !== -1;
          return (
            <g key={i} style={{cursor:'pointer'}} onClick={() => handleHexClick({q:hex.q, r:hex.r})}>
              <polygon
                points={getHexPoints(x, y, HEX_SIZE)}
                fill={isSelected ? '#1976d2aa' : fill}
                stroke={isSelected ? '#1976d2' : '#888'}
                strokeWidth={isSelected ? 4 : 1}
              />
              {/* Координаты q,r по центру hex-а, очень мелко */}
              <text
                x={x}
                y={y+3}
                fontSize={7}
                fill="#bbb"
                textAnchor="middle"
                alignmentBaseline="middle"
                style={{userSelect:'none'}}
              >
                {hex.q},{hex.r}
              </text>
            </g>
          );
        })}
        {/* --- Ресурсы --- */}
        {mappedResources.map((res, i) => {
          const { x, y } = hexToPixel(res.q, res.r);
          const t = String(res.type);
          const info = RESOURCE_TYPE_MAP[t];
          if (!info) return null;
          // Рисуем иконку ресурса
          return (
            <g key={i} transform={`translate(${x-11},${y-11})`}>
              {info.icon()}
            </g>
          );
        })}
        {/* --- Наши муравьи --- */}
        {mappedAnts.map((ant, i) => {
          const { x, y } = hexToPixel(ant.q, ant.r);
          const t = String(ant.type);
          let symbol = '?', color = '#888';
          if (t === '0' || t === 'worker') { symbol = '■'; color = '#1976d2'; }
          if (t === '1' || t === 'fighter') { symbol = '●'; color = '#d32f2f'; }
          if (t === '2' || t === 'scout') { symbol = '△'; color = '#388e3c'; }
          // --- Если муравей несёт еду, делаем крупнее и добавляем звёздочку ---
          const hasFood = ant.food && Number(ant.food.amount) > 0;
          return (
            <g key={i}>
              <text
                x={x-6}
                y={y+4}
                fontSize={hasFood ? 22 : 14}
                fill={color}
                style={{userSelect:'none', fontWeight: hasFood ? 700 : 400}}
              >
                {symbol}
              </text>
              {hasFood && (
                <text
                  x={x+10}
                  y={y-8}
                  fontSize={16}
                  fill="#ffb300"
                  style={{userSelect:'none'}}
                >
                  ★
                </text>
              )}
            </g>
          );
        })}
        {/* --- Враги --- */}
        {mappedEnemies.map((e, i) => {
          const { x, y } = hexToPixel(e.q, e.r);
          const t = String(e.type);
          return (
            <text key={i} x={x-6} y={y+4} fontSize={14} fill="#d32f2f">&#x2716;</text>
          );
        })}
      </svg>
      {/* --- Координаты q (сверху, строго по центру hex-ов верхнего ряда) --- */}
      <div style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: width,
        height: 40,
        pointerEvents: 'none',
        zIndex: 2,
      }}>
        {allQ.map((q, i) => {
          const { x, y } = hexToPixel(q, minR - PAD);
          return <span key={i} style={{ position: 'absolute', left: x-12, top: y-24, fontSize: 18, fontWeight: 700, color: '#222', background: 'rgba(255,255,255,0.7)', padding: '0 2px', borderRadius: 3 }}>{q}</span>;
        })}
      </div>
      {/* --- Координаты r (слева, строго по центру hex-ов) --- */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        height: height,
        width: 48,
        pointerEvents: 'none',
        zIndex: 2,
      }}>
        {allR.map((r, i) => {
          const { y } = hexToPixel(minQ - PAD, r);
          return <span key={i} style={{ position: 'absolute', top: y-12, left: 8, fontSize: 18, fontWeight: 700, color: '#222', background: 'rgba(255,255,255,0.7)', padding: '0 2px', borderRadius: 3 }}>{r}</span>;
        })}
      </div>
      {/* Легенда (только три типа муравьев) */}
      <div style={{
        marginTop: 24,
        left: 0,
        width: width,
        background: 'rgba(255,255,255,0.95)',
        border: '1px solid #aaa',
        borderTop: 'none',
        fontSize: 14,
        padding: 8,
        display: 'flex',
        flexWrap: 'wrap',
        gap: 16,
        alignItems: 'center',
        zIndex: 2
      }}>
        <LegendHex color="#ffe066" label="Муравейник (nest/home)" />
        <LegendHex color="#e0e0e0" label="Пустой (empty) — проходимо" />
        <LegendHex color="#a67c52" label="Грязь (mud) — ОП x2" />
        <LegendHex color="#e57373" label="Кислота (acid) — опасно" />
        <LegendHex color="#555" label="Камни (rock/stone) — НЕпроходимо" />
        <LegendHex color="#ccc" label="Неизвестно (unknown)" />
        <ResourceLegend type={1} />
        <ResourceLegend type={2} />
        <ResourceLegend type={3} />
        <span style={{color:'#1976d2',marginLeft:16}}>■</span> — Worker
        <span style={{color:'#d32f2f'}}>●</span> — Fighter
        <span style={{color:'#388e3c'}}>△</span> — Scout
        <span style={{color:'#d32f2f',marginLeft:16}}>&#x2716;</span> — Enemy
        <span style={{marginLeft:16, fontSize:18, color:'#ffb300'}}>★</span> — Муравей несёт еду (больше, выделен)
      </div>
    </div>
  );
};

export default HexMap;
