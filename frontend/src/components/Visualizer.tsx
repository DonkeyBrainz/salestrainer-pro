import React, { useRef, useEffect } from 'react';

interface VisualizerProps {
  analyser: AnalyserNode | null;
  isActive: boolean;
  color?: string;
  variant?: 'wave' | 'bars';
}

const Visualizer: React.FC<VisualizerProps> = ({ analyser, isActive, color = '#A0522D', variant = 'wave' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    const bufferLength = analyser ? analyser.frequencyBinCount : 0;
    const dataArray = analyser ? new Uint8Array(bufferLength) : new Uint8Array(0);

    const render = () => {
      // Resize handling
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);

      const width = rect.width;
      const height = rect.height;
      const centerY = height / 2;

      ctx.clearRect(0, 0, width, height);

      if (isActive && analyser) {
        if (variant === 'wave') {
            // WAVE MODE (Time Domain) - Best for AI Voice output
            analyser.getByteTimeDomainData(dataArray);
            ctx.lineWidth = 2;
            ctx.strokeStyle = color;
            ctx.beginPath();

            const sliceWidth = width * 1.0 / bufferLength;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
                const v = dataArray[i] / 128.0;
                const y = v * centerY;

                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    const prevV = dataArray[i-1] / 128.0;
                    const prevY = prevV * centerY;
                    const prevX = x - sliceWidth;
                    const midX = (prevX + x) / 2;
                    const midY = (prevY + y) / 2;
                    ctx.quadraticCurveTo(prevX, prevY, midX, midY);
                }
                x += sliceWidth;
            }

            ctx.lineTo(width, height / 2);
            ctx.stroke();
        } else {
            // BARS MODE (Frequency Domain) - Best for User Mic Input
            analyser.getByteFrequencyData(dataArray);
            ctx.fillStyle = color;
            
            // Draw fewer, wider bars for a cleaner "voice recorder" look
            const barCount = 24; 
            const step = Math.floor(bufferLength / barCount);
            const barWidth = (width / barCount) * 0.6; // Gap ratio
            const gap = (width / barCount) * 0.4;
            
            for (let i = 0; i < barCount; i++) {
                const dataIndex = Math.floor(i * step); 
                const v = dataArray[dataIndex] / 255.0; // Normalized 0-1
                
                // Make bars symmetric around center
                const barHeight = Math.max(2, v * height * 0.8);
                const x = i * (barWidth + gap) + gap/2;
                const y = centerY - (barHeight / 2);
                
                // Use standard rect to avoid compatibility issues with roundRect
                ctx.beginPath();
                ctx.rect(x, y, barWidth, barHeight);
                ctx.fill();
            }
        }
      } else {
        // Idle State
        ctx.lineWidth = 1;
        ctx.strokeStyle = color + '40'; // Low opacity
        ctx.beginPath();
        ctx.moveTo(0, centerY);
        ctx.lineTo(width, centerY);
        ctx.stroke();
      }

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [analyser, isActive, color, variant]);

  return (
    <canvas 
      ref={canvasRef} 
      className="w-full h-full"
    />
  );
};

export default Visualizer;