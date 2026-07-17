import React from 'react';
import { VT } from '@/styles/voiceprint';

interface DraftingLoaderProps {
  show: boolean;
  label: string;
  subtext: string;
}

/** Full-screen blueprint overlay shown while data-heavy rooms load. */
export function DraftingLoader({ show, label, subtext }: DraftingLoaderProps) {
  if (!show) return null;

  return (
    <div className="draft-loader-overlay">
      <svg className="dl-svg" viewBox="0 0 240 180" aria-hidden="true" style={{ width: 260, height: 200, overflow: 'visible' }}>
        <path className="dl-ghost" d="M40 35 H200 V145 H40 Z" />
        <path className="dl-outline" d="M40 35 H200 V145 H40 Z" />
        <g className="dl-pencil">
          <g className="dl-bob">
            <polygon points="0,0 6,10 12,4" fill="#2b2b2b" />
            <polygon points="6,10 12,4 20,16 14,22" fill="#e4c063" />
            <polygon points="14,22 20,16 44,40 38,46" fill={VT.amber} />
            <polygon points="38,46 44,40 50,46 44,52" fill="#9aa6b2" />
            <polygon points="44,52 50,46 55,51 49,57" fill="#e88b8b" />
          </g>
        </g>
      </svg>
      <div style={{ fontFamily: VT.oswald, fontWeight: 600, letterSpacing: '0.26em', textTransform: 'uppercase', fontSize: 13, color: VT.text }}>
        Drafting <b style={{ color: VT.amber, fontWeight: 600 }}>{label}</b><span className="dl-dots" />
      </div>
      <div style={{ fontFamily: VT.mono, fontSize: 10, letterSpacing: '0.14em', color: VT.textMuted, textTransform: 'uppercase' }}>
        {subtext}
      </div>
    </div>
  );
}

export default DraftingLoader;
