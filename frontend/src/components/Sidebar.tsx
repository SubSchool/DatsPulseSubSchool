import React from 'react';

interface Props {
  turn: number;
  score: number;
  antsCount: number;
  log: string[];
}

const Sidebar: React.FC<Props> = ({ turn, score, antsCount, log }) => (
  <div style={{ width: 260, background: '#fafafa', padding: 12, borderLeft: '1px solid #ccc', height: 600, overflowY: 'auto' }}>
    <div>Turn: {turn}</div>
    <div>Score: {score}</div>
    <div>Ants: {antsCount}</div>
    <div style={{ marginTop: 16, fontWeight: 'bold' }}>Log:</div>
    <div style={{ fontSize: 12, whiteSpace: 'pre-line' }}>
      {log.map((l, i) => <div key={i}>{l}</div>)}
    </div>
  </div>
);

export default Sidebar;
