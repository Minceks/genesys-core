import React, { useRef, useEffect } from 'react';
import './App.css';

const PARTICLE_COUNT = 180;

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
}

const App: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', resize);
    resize();

    const particles: Particle[] = [];

    const createParticle = (): Particle => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.6,
      vy: (Math.random() - 0.5) * 0.6,
      size: 2 + Math.random() * 3,
    });

    for (let i = 0; i < PARTICLE_COUNT; i++) particles.push(createParticle());

    const animate = () => {
      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const grad = ctx.createRadialGradient(
        canvas.width / 2,
        canvas.height / 2,
        0,
        canvas.width / 2,
        canvas.height / 2,
        canvas.width
      );
      grad.addColorStop(0, 'rgba(0,217,255,0.08)');
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = '#00d9ff';
        ctx.shadowColor = '#00d9ff';
        ctx.shadowBlur = 20;
        ctx.fill();
      });

      requestAnimationFrame(animate);
    };
    animate();

    return () => {
      window.removeEventListener('resize', resize);
    };
  }, []);

  const startGame = () => {
    // Placeholder for game start logic
    alert('Expedition begins...');
  };

  return (
    <div className="app">
      <canvas ref={canvasRef} />
      <h1 className="title">LUXURY SURVIVOR</h1>
      <button className="startBtn" onClick={startGame}>
        Start Expedition
      </button>
    </div>
  );
};

export default App;