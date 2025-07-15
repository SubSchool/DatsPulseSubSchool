import React from 'react';
import type { JSX } from 'react';

// ... интерфейсы Hex, Ant, Enemy, Resource (копипастим из HexMap)
interface Hex { q: number; r: number; type: string; _color?: string; }
interface Ant { id: string; q: number; r: number; type: string; hp: number; carryingType?: string; carryingAmt?: number; }
interface Enemy { id: string; q: number; r: number; type: string; hp: number; }
interface Resource { q: number; r: number; type: string; amount: number; }

interface Props { arenaJson: string; }

const HEX_SIZE = 24;
const SQRT3 = Math.sqrt(3);
const PADDING = 32; // компактный отступ сверху, слева, снизу
const COORD_OFFSET = 32; // px отступ для координат
const BOTTOM_PADDING = 56; // px отступ снизу

function getHexPoints(x: number, y: number, size: number) {
  const points = [];
  for (let i = 0; i < 6; i++) {
    const angle = Math.PI / 3 * i + Math.PI / 6; // для ровных сот
    points.push([
      x + size * Math.cos(angle),
      y + size * Math.sin(angle)
    ]);
  }
  return points.map(p => p.join(",")).join(" ");
}

// --- Новый TYPE_MAP по документации ---
const TYPE_MAP: Record<number, {name: string, color: string}> = {
  1: { name: 'nest', color: '#ffe066' },      // муравейник
  2: { name: 'empty', color: '#e0e0e0' },    // пустой
  3: { name: 'mud', color: '#a67c52' },      // грязь
  4: { name: 'acid', color: '#e57373' },     // кислота
  5: { name: 'rock', color: '#555' },        // камни (непроходимо)
  0: { name: 'unknown', color: '#ccc' },     // неизвестно
};

const LegendHex: React.FC<{color:string,label:string}> = ({color,label}) => (
  <span style={{display:'inline-flex',alignItems:'center',marginRight:12}}>
    <svg width={22} height={22} style={{marginRight:4}}>
      <polygon points={getHexPoints(11,11,10)} fill={color} stroke="#888" strokeWidth={1}/>
    </svg>
    {label}
  </span>
);

// --- Маппинг типов ресурсов ---
const RESOURCE_TYPE_MAP: Record<number, {name: string, color: string, icon: (props?: any) => JSX.Element}> = {
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
};

// --- Легенда для ресурса ---
const ResourceLegend: React.FC<{type: number}> = ({type}) => {
  const res = RESOURCE_TYPE_MAP[type];
  return (
    <span style={{display:'inline-flex',alignItems:'center',marginRight:12}}>
      <svg width={22} height={22} style={{marginRight:4}}>{res.icon()}</svg>
      {res.name}
    </span>
  );
};

// --- Легенда для муравья ---
const AntLegend: React.FC<{type: number}> = ({type}) => {
  let symbol = '', color = '', label = '';
  if (type === 0) { symbol = '■'; color = '#1976d2'; label = 'Worker (рабочий)'; }
  if (type === 1) { symbol = '●'; color = '#d32f2f'; label = 'Fighter (боец)'; }
  if (type === 2) { symbol = '△'; color = '#388e3c'; label = 'Scout (разведчик)'; }
  return <span style={{display:'inline-flex',alignItems:'center',marginRight:12}}><span style={{fontSize:18,color,marginRight:4}}>{symbol}</span>{label}</span>;
};

export const HexMap_test: React.FC<Props> = ({ arenaJson }) => {
  let map: Hex[] = [], ants: Ant[] = [], enemies: Enemy[] = [], resources: Resource[] = [];
  try {
    const data = JSON.parse(arenaJson);
    map = data.map || [];
    ants = data.ants || [];
    enemies = data.enemies || [];
    resources = data.food || [];
    // --- Маппим числовые типы в строковые и цвета ---
    map = map.map(cell => {
      let t = String(cell.type);
      const info = TYPE_MAP[Number(t)] || TYPE_MAP[0];
      return { ...cell, type: info.name, _color: info.color };
    });
  } catch (e) {
    return <div style={{color:'red'}}>Ошибка парсинга JSON</div>;
  }
  if (!map.length) return <div>Нет карты для отображения</div>;

  // --- Координатные границы ---
  const qs = map.map(h => h.q);
  const rs = map.map(h => h.r);
  const minQ = Math.min(...qs);
  const maxQ = Math.max(...qs);
  const minR = Math.min(...rs);
  const maxR = Math.max(...rs);
  const PAD = 1;

  // --- Прямоугольная сетка для hex-ов ---
  const fullHexes: Record<string, Hex> = {};
  map.forEach(h => { fullHexes[`${h.q},${h.r}`] = h; });
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
  // --- Квадрат сетки ---
  const squareToPixel = (q: number, r: number) => {
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
  // Для каждого q ищем минимальный r, где есть hex
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

  // --- Функция для смещения точки наружу по нормали к линии ---
  function offsetAlongNormal(points: {x:number, y:number}[], idx: number, offset: number) {
    // Берём вектор между соседями (или ближайший край)
    const prev = points[Math.max(0, idx-1)];
    const next = points[Math.min(points.length-1, idx+1)];
    // Вектор вдоль линии
    const dx = next.x - prev.x;
    const dy = next.y - prev.y;
    // Нормаль (перпендикуляр, наружу)
    const len = Math.sqrt(dx*dx + dy*dy) || 1;
    const nx = -dy/len;
    const ny = dx/len;
    // Смещаем наружу
    return {x: points[idx].x + nx*offset, y: points[idx].y + ny*offset};
  }

  // --- Размер SVG ---
  const width = PADDING + COORD_OFFSET + HEX_SIZE * SQRT3 * (maxQ - minQ + 3 + (maxR - minR + 3)/2) + PADDING;
  const height = PADDING + COORD_OFFSET + HEX_SIZE * 3/2 * (maxR - minR + 3) + PADDING + BOTTOM_PADDING;

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
          return (
            <g key={i}>
              <polygon
                points={getHexPoints(x, y, HEX_SIZE)}
                fill={fill}
                stroke="#888"
                strokeWidth={1}
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
        {resources.map((res, i) => {
          const { x, y } = hexToPixel(res.q, res.r);
          const t = typeof res.type === 'string' ? parseInt(res.type) : res.type;
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
        {ants.map((ant, i) => {
          const { x, y } = hexToPixel(ant.q, ant.r);
          const t = Number(ant.type);
          let symbol = '?', color = '#888';
          if (t === 0) { symbol = '■'; color = '#1976d2'; }
          if (t === 1) { symbol = '●'; color = '#d32f2f'; }
          if (t === 2) { symbol = '△'; color = '#388e3c'; }
          return (
            <text key={i} x={x-6} y={y+4} fontSize={14} fill={color} style={{userSelect:'none'}}>
              {symbol === '?' ? '?' : symbol === '■' ? '■' : symbol === '●' ? '●' : symbol === '△' ? '△' : '?'}
            </text>
          );
        })}
        {/* --- Враги --- */}
        {enemies.map((e, i) => {
          const { x, y } = hexToPixel(e.q, e.r);
          return (
            <text key={i} x={x-6} y={y+4} fontSize={14} fill="#d32f2f">\u2716</text>
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
        <AntLegend type={2} />
        <AntLegend type={1} />
        <AntLegend type={0} />
        <span style={{color:'#d32f2f',marginLeft:16}}>&#x2716;</span> — Enemy
      </div>
    </div>
  );
}; 