import React, { useRef, useEffect } from 'react';
import { AppMode } from '@/types';

interface AmbientBackgroundProps {
  mode: AppMode | null;
  audioLevel: number; // 0 to 1 normalized RMS
  sentiment?: 'neutral' | 'positive' | 'warning';
}

const AmbientBackground: React.FC<AmbientBackgroundProps> = ({ mode, audioLevel, sentiment = 'neutral' }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Helper to convert Hex to RGBA
  const hexToRgba = (hex: string, alpha: number) => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  // Configuration per mode with sentiment variations
  const getPalette = (m: AppMode | null, s: 'neutral' | 'positive' | 'warning') => {
    switch (m) {
      case AppMode.SAFE_SPACE:
        // Calming Emeralds/Sages
        if (s === 'positive') return ['#ECFDF5', '#D1FAE5', '#6EE7B7', '#34D399']; // Brighter Mint
        if (s === 'warning') return ['#ECFDF5', '#D1FAE5', '#FCD34D', '#F59E0B']; // Hint of concern (Amber)
        return ['#ECFDF5', '#D1FAE5', '#A7F3D0', '#34D399']; // Standard

      case AppMode.EVALUATION:
        // Cool Slates/Greys/Reds - Serious Tone
        if (s === 'positive') return ['#F8FAFC', '#E0F2FE', '#BAE6FD', '#7DD3FC']; // Blue hint for success
        if (s === 'warning') return ['#FEF2F2', '#FEE2E2', '#FCA5A5', '#EF4444']; // Red alert
        return ['#F8FAFC', '#F1F5F9', '#E2E8F0', '#94A3B8']; // Neutral Slate

      case AppMode.TRAINING:
      default:
        // Warm Stone/Gold - Professional
        if (s === 'positive') return ['#FAFAF9', '#FEFCE8', '#FEF08A', '#D4B996']; // Golden Glow
        if (s === 'warning') return ['#FAFAF9', '#FFF7ED', '#FFEDD5', '#D97706']; // Rust warning
        return ['#FAFAF9', '#F5F5F4', '#E7E5E4', '#D4B996']; // Neutral
    }
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    // Create blobs with varied properties
    const blobs = [
      { x: width * 0.2, y: height * 0.2, r: 400, dx: 0.5, dy: 0.5, colorIdx: 0 },
      { x: width * 0.8, y: height * 0.8, r: 500, dx: -0.5, dy: -0.5, colorIdx: 1 },
      { x: width * 0.5, y: height * 0.5, r: 300, dx: 0.3, dy: -0.3, colorIdx: 2 },
      { x: width * 0.8, y: height * 0.2, r: 350, dx: -0.4, dy: 0.4, colorIdx: 3 },
    ];

    let animationFrameId: number;

    const render = () => {
      // Cast sentiment to ensure it matches the union type expected by getPalette
      // Even though prop types enforce this, TS might widen it to string in some contexts
      const palette = getPalette(mode, sentiment as 'neutral' | 'positive' | 'warning');

      // Resize handling
      if (canvas.width !== window.innerWidth || canvas.height !== window.innerHeight) {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
      }

      ctx.clearRect(0, 0, width, height);

      // Draw background base
      ctx.fillStyle = palette[0];
      ctx.fillRect(0, 0, width, height);

      // --- DYNAMIC PHYSICS CALCULATIONS ---

      // 1. Audio Reactivity: Louder audio = Faster Movement + Larger Radius
      const audioPulse = Math.min(audioLevel * 300, 150);
      const speedMultiplier = 1 + (audioLevel * 4); // Up to 5x speed during loud moments

      // 2. Mode-Specific Physics
      let modeSpeedBase = 1.0;
      let breathingEffect = 0;
      let sharpness = 0; // 0 = soft (default), 1 = sharper gradients

      if (mode === AppMode.SAFE_SPACE) {
        modeSpeedBase = 0.5; // Slow down for calm
        // Sine wave breathing effect (approx 4 second cycle)
        breathingEffect = Math.sin(Date.now() / 2000) * 20;
      } else if (mode === AppMode.EVALUATION) {
        modeSpeedBase = 1.8; // Faster, busier for testing
        sharpness = 0.4; // Harder edges
      }

      blobs.forEach((blob, i) => {
        // Apply Movement
        blob.x += blob.dx * modeSpeedBase * speedMultiplier;
        blob.y += blob.dy * modeSpeedBase * speedMultiplier;

        // Bounce off walls (with large margin)
        if (blob.x < -blob.r) blob.dx = Math.abs(blob.dx);
        if (blob.x > width + blob.r) blob.dx = -Math.abs(blob.dx);
        if (blob.y < -blob.r) blob.dy = Math.abs(blob.dy);
        if (blob.y > height + blob.r) blob.dy = -Math.abs(blob.dy);

        // Calculate Radius
        const currentRadius = blob.r + audioPulse + breathingEffect;

        // Draw Gradient Blob
        ctx.beginPath();

        const gradient = ctx.createRadialGradient(
          blob.x, blob.y, 0,
          blob.x, blob.y, currentRadius
        );

        const colorHex = palette[blob.colorIdx % palette.length];

        // Dynamic Alpha: Boost brightness when audio is detected
        const alphaBoost = audioLevel * 0.3;

        // Gradient Stops - Evaluation mode makes these tighter for a "sharper" look
        const coreStop = 0 + (sharpness * 0.1);
        const midStop = 0.5 + (sharpness * 0.2);

        gradient.addColorStop(coreStop, hexToRgba(colorHex, 0.6 + alphaBoost)); // Core
        gradient.addColorStop(midStop, hexToRgba(colorHex, 0.3 + (alphaBoost/2))); // Mid
        gradient.addColorStop(1, hexToRgba(colorHex, 0)); // Edge transparent

        ctx.fillStyle = gradient;

        // Blend Mode: 'multiply' gives that watercolor look, 'overlay' is more intense
        ctx.globalCompositeOperation = mode === AppMode.EVALUATION ? 'hard-light' : 'multiply';

        ctx.arc(blob.x, blob.y, currentRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalCompositeOperation = 'source-over'; // Reset
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animationFrameId);
  }, [mode, audioLevel, sentiment]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none -z-10 transition-colors duration-1000"
    />
  );
};

export default AmbientBackground;
