import React, { useEffect, useRef } from 'react';

type DataPoint = { x: number; y: number };
type DataChartProps = {
  data: DataPoint[];
  width?: number;
  height?: number;
};

export const DataChart: React.FC<DataChartProps> = ({
  data,
  width = 800,
  height = 400,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear
    ctx.clearRect(0, 0, width, height);
    // Background
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, width, height);

    // Neon line style
    ctx.strokeStyle = '#00d9ff';
    ctx.lineWidth = 2;
    ctx.shadowColor = '#00d9ff';
    ctx.shadowBlur = 15;

    // Scale data to canvas
    const padding = 40;
    const maxX = Math.max(...data.map(d => d.x));
    const maxY = Math.max(...data.map(d => d.y));
    const minX = Math.min(...data.map(d => d.x));
    const minY = Math.min(...data.map(d => d.y));

    const scaleX = (width - padding * 2) / (maxX - minX || 1);
    const scaleY = (height - padding * 2) / (maxY - minY || 1);

    const points = data.map(d => ({
      x: padding + (d.x - minX) * scaleX,
      y: height - padding - (d.y - minY) * scaleY,
    }));

    // Draw line
    ctx.beginPath();
    points.forEach((p, i) => {
      i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
    });
    ctx.stroke();

    // Draw axes
    ctx.shadowBlur = 0;
    ctx.strokeStyle = '#00d9ff';
    ctx.lineWidth = 1;
    ctx.beginPath();
    // X axis
    ctx.moveTo(padding, height - padding);
    ctx.lineTo(width - padding, height - padding);
    // Y axis
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, height - padding);
    ctx.stroke();
  }, [data, width, height]);

  return <canvas ref={canvasRef} width={width} height={height} className="rounded-md" />;
};