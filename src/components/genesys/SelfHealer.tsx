import React, { useEffect, useState } from 'react';
import { Activity, ShieldAlert } from 'lucide-react';

interface SelfHealerProps {
  previewCode: string; // This is the broken code
  onRepair: (errorPrompt: string) => void;
  isBusy: boolean;
}

export function SelfHealer({ previewCode, onRepair, isBusy }: SelfHealerProps) {
  const [lastError, setLastError] = useState<string | null>(null);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === 'SYSTEM_CRASH' && !isBusy) {
        const errorMsg = event.data.error;
        setLastError(errorMsg);
        
        // --- THE "MEMORY" UPGRADE ---
        // We now send the broken code back to the AI so it has context.
        const repairPrompt = `
          CRITICAL ERROR DETECTED IN THE PREVIEW.
          
          ERROR MESSAGE: "${errorMsg}"
          
          THE BROKEN CODE WAS:
          \`\`\`html
          ${previewCode}
          \`\`\`
          
          TASK: You provided broken code. Fix it now. 
          Define any missing functions (like 'boom').
          Output the full corrected <GENESYS_PREVIEW> and ---FILE--- blocks.
        `;

        onRepair(repairPrompt);
        setTimeout(() => setLastError(null), 5000);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [previewCode, isBusy, onRepair]);

  if (!lastError && !isBusy) return null;

  return (
    <div className="absolute bottom-6 right-6 z-50 animate-in fade-in slide-in-from-bottom-4">
      <div className={`p-4 rounded-2xl border backdrop-blur-xl flex items-center gap-3 shadow-2xl ${lastError ? 'bg-red-500/10 border-red-500/50' : 'bg-blue-500/10 border-blue-500/50'}`}>
        {lastError ? (
          <ShieldAlert className="text-red-500 animate-pulse" size={20} />
        ) : (
          <Activity className="text-blue-400 animate-spin" size={20} />
        )}
        <div>
          <p className={`text-[10px] font-black uppercase tracking-widest ${lastError ? 'text-red-500' : 'text-blue-400'}`}>
            {lastError ? 'Crash Detected' : 'Surgery in Progress'}
          </p>
          <p className="text-[11px] text-white/70 font-mono">
            {lastError ? lastError.slice(0, 30) + '...' : 'Reconstructing Logic...'}
          </p>
        </div>
      </div>
    </div>
  );
}
