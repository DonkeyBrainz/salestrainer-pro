import React, { useEffect, useRef } from 'react';

interface SpeakerUnitProps {
  analyser: AnalyserNode | null;
  isActive: boolean;
}

const BINS = 32;

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/**
 * Blueprint "speaker unit" schematic: rounded box, corner screws, concentric
 * dot rings, center cone, 5 LED lights. Energy is read from a real
 * AnalyserNode (input analyser while the user speaks, output while the AI
 * speaks) rather than the original mockup's randomized bursts.
 */
export default function SpeakerUnit({ analyser, isActive }: SpeakerUnitProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const bins = new Float32Array(BINS).fill(0);
    let energy = 0;
    let rafId = 0;
    let freqData: Uint8Array | null = null;

    function resize() {
      if (!canvas) return;
      const rect = canvas.parentElement!.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    window.addEventListener('resize', resize);
    const resizeTimer = setTimeout(resize, 30);

    function sampleBins() {
      if (!analyser || !isActive) {
        for (let i = 0; i < BINS; i++) bins[i] += (0 - bins[i]) * 0.12;
        return;
      }
      if (!freqData || freqData.length !== analyser.frequencyBinCount) {
        freqData = new Uint8Array(analyser.frequencyBinCount);
      }
      analyser.getByteFrequencyData(freqData);
      const perBin = Math.max(1, Math.floor(freqData.length / BINS));
      for (let i = 0; i < BINS; i++) {
        let sum = 0;
        for (let j = 0; j < perBin; j++) sum += freqData[i * perBin + j] ?? 0;
        const target = Math.min(1, (sum / perBin / 255) * 1.8);
        bins[i] += (target - bins[i]) * 0.35;
      }
    }

    function frame() {
      rafId = requestAnimationFrame(frame);
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const w = rect.width, h = rect.height;
      if (w === 0) return;
      if (canvas.width === 0) resize();
      ctx!.clearRect(0, 0, w, h);

      sampleBins();
      let e = 0;
      for (let i = 0; i < BINS; i++) e += bins[i];
      energy += (e / BINS - energy) * 0.15;

      const cx = w / 2, cy = h / 2;
      const boxW = w * 0.5, boxH = h * 0.6;

      ctx!.strokeStyle = 'rgba(255,255,255,0.55)';
      ctx!.lineWidth = 1.4;
      roundRect(ctx!, cx - boxW / 2, cy - boxH / 2, boxW, boxH, 10);
      ctx!.stroke();

      ctx!.fillStyle = 'rgba(255,255,255,0.4)';
      const sOff = 12;
      ([
        [cx - boxW / 2 + sOff, cy - boxH / 2 + sOff],
        [cx + boxW / 2 - sOff, cy - boxH / 2 + sOff],
        [cx - boxW / 2 + sOff, cy + boxH / 2 - sOff],
        [cx + boxW / 2 - sOff, cy + boxH / 2 - sOff],
      ] as const).forEach(([x, y]) => {
        ctx!.beginPath();
        ctx!.arc(x, y, 2.4, 0, Math.PI * 2);
        ctx!.fill();
      });

      const rings = 5;
      const maxR = Math.min(boxW, boxH) * 0.36;
      for (let r = 1; r <= rings; r++) {
        const rad = (r / rings) * maxR;
        const count = r * 7;
        for (let i = 0; i < count; i++) {
          const a = (i / count) * Math.PI * 2 + r * 0.15;
          const x = cx + Math.cos(a) * rad, y = cy + Math.sin(a) * rad;
          const binIdx = Math.floor(((a + Math.PI) / (Math.PI * 2)) * BINS) % BINS;
          const b = bins[binIdx];
          ctx!.beginPath();
          ctx!.arc(x, y, 1.6, 0, Math.PI * 2);
          ctx!.fillStyle = `rgba(255,255,255,${0.15 + b * 0.75})`;
          ctx!.fill();
        }
      }

      const coneR = 6 + energy * 9;
      ctx!.save();
      ctx!.shadowColor = 'rgba(255,255,255,0.6)';
      ctx!.shadowBlur = 16;
      ctx!.beginPath();
      ctx!.arc(cx, cy, coneR, 0, Math.PI * 2);
      ctx!.fillStyle = isActive ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.4)';
      ctx!.fill();
      ctx!.restore();

      const ledCount = 5;
      const lit = Math.round(energy * ledCount * 1.6);
      const ledY = cy + boxH / 2 - 16;
      const ledSpan = boxW * 0.44;
      for (let i = 0; i < ledCount; i++) {
        const x = cx - ledSpan / 2 + (i / (ledCount - 1)) * ledSpan;
        const on = i < lit;
        ctx!.save();
        if (on) {
          ctx!.shadowColor = 'rgba(240,162,78,0.9)';
          ctx!.shadowBlur = 10;
        }
        ctx!.beginPath();
        ctx!.arc(x, ledY, 2.6, 0, Math.PI * 2);
        ctx!.fillStyle = on ? 'rgba(240,162,78,0.95)' : 'rgba(255,255,255,0.15)';
        ctx!.fill();
        ctx!.restore();
      }
    }
    rafId = requestAnimationFrame(frame);

    return () => {
      window.removeEventListener('resize', resize);
      clearTimeout(resizeTimer);
      cancelAnimationFrame(rafId);
    };
  }, [analyser, isActive]);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
    </div>
  );
}
