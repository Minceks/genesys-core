import React from 'react';

const Welcome: React.FC = () => {
  return (
    <div className="flex items-center justify-center h-screen bg-black">
      {/* Neon “WELCOME” sign */}
      <h1 className="text-8xl font-bold text-[#00ffff] neon-glow font-sora">
        WELCOME
      </h1>
    </div>
  );
};

export default Welcome;

/* Tailwind custom utilities (add to your global CSS if not using the preview) */
@layer utilities {
  .neon-glow {
    text-shadow:
      0 0 5px #00ffff,
      0 0 10px #00ffff,
      0 0 20px #00ffff,
      0 0 40px #00ffff;
  }
}