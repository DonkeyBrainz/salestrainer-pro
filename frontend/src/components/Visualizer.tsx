import React, { useRef, useEffect } from 'react';
import { AT } from '@/styles/tokens';

interface CircularWaveformProps {
  analyser: AnalyserNode | null;
  isActive: boolean;
  label?: string;
  initial?: string;
}

const BARS = 56;
const R_INNER = 90;
const MAX_AMP = 36;

function getStaticAmplitudes(): number[] {
  return Array.from({ length: BARS }, (_, i) =>
    Math.max(0.2, (Math.sin(i * 0.7) + Math.cos(i * 1.3) + 2) / 4)
  );
}

const CircularWaveform: React.FC<CircularWaveformProps> = ({
  analyser,
  isActive,
  label = 'AI',
  initial = 'A',
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const rafRef = useRef<number | null>(null);
  const staticAmps = useRef(getStaticAmplitudes());

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const lines = svg.querySelectorAll<SVGLineElement>('line[data-bar]');

    const bufferLength = analyser ? analyser.frequencyBinCount : 0;
    const dataArray = analyser ? new Uint8Array(bufferLength) : new Uint8Array(0);

    const step = bufferLength > 0 ? Math.floor(bufferLength / BARS) : 1;

    const animate = () => {
      let amps: number[];

      if (isActive && analyser && bufferLength > 0) {
        analyser.getByteFrequencyData(dataArray);
        amps = Array.from({ length: BARS }, (_, i) => {
          const val = dataArray[i * step] / 255;
          return Math.max(0.15, val);
        });
      } else {
        amps = staticAmps.current;
      }

      lines.forEach((line, i) => {
        const amp = amps[i] ?? 0.2;
        const a = (i / BARS) * Math.PI * 2;
        const r1 = R_INNER;
        const r2 = R_INNER + amp * MAX_AMP;
        const x1 = Math.cos(a) * r1;
        const y1 = Math.sin(a) * r1;
        const x2 = Math.cos(a) * r2;
        const y2 = Math.sin(a) * r2;

        line.setAttribute('x1', String(x1));
        line.setAttribute('y1', String(y1));
        line.setAttribute('x2', String(x2));
        line.setAttribute('y2', String(y2));
        line.setAttribute('opacity', String(0.5 + amp * 0.5));
      });

      rafRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [analyser, isActive]);

  const initialAmps = staticAmps.current;

  return (
    <div style={{ position: 'relative', width: 280, height: 280, display: 'grid', placeItems: 'center' }}>
      <svg
        ref={svgRef}
        width="280"
        height="280"
        viewBox="-140 -140 280 280"
        style={{ position: 'absolute', inset: 0 }}
      >
        {/* Static bar elements — positions updated via RAF */}
        {initialAmps.map((amp, i) => {
          const a = (i / BARS) * Math.PI * 2;
          const r1 = R_INNER;
          const r2 = R_INNER + amp * MAX_AMP;
          const x1 = Math.cos(a) * r1;
          const y1 = Math.sin(a) * r1;
          const x2 = Math.cos(a) * r2;
          const y2 = Math.sin(a) * r2;
          const color = i < BARS / 3 ? AT.terra : i < (2 * BARS) / 3 ? AT.butter : AT.sage;
          return (
            <line
              key={i}
              data-bar={i}
              x1={x1} y1={y1}
              x2={x2} y2={y2}
              stroke={color}
              strokeWidth="3"
              strokeLinecap="round"
              opacity={0.5 + amp * 0.5}
            />
          );
        })}

        <circle r="80" cx="0" cy="0" fill="none" stroke={AT.hair} strokeWidth="1" />
        <circle r="60" cx="0" cy="0" fill={AT.surface2} stroke={AT.hair} strokeWidth="1" />
      </svg>

      {/* Center label */}
      <div style={{
        position: 'relative',
        width: 120, height: 120,
        borderRadius: '50%',
        display: 'grid', placeItems: 'center',
        textAlign: 'center',
      }}>
        <div>
          <div style={{ fontFamily: AT.display, fontSize: 28, fontWeight: 700, color: AT.ink, lineHeight: 1 }}>{initial}</div>
          <div style={{ fontFamily: AT.mono, fontSize: 9.5, letterSpacing: '0.16em', color: AT.inkMuted, marginTop: 4, textTransform: 'uppercase' }}>
            {label}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CircularWaveform;
