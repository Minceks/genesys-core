import { createRoute } from "@tanstack/react-router";
import { Route as rootRoute } from "./__root";
import React, { useState, useEffect, useRef } from "react";
import { Navbar } from "@/components/genesys/navbar";
import { askGenesys } from "@/utils/ai.functions";
import { SelfHealer } from "@/components/genesys/SelfHealer";
import { 
  Send, Brain, ListChecks, Loader2, Eye, 
  FileCode, RefreshCw, Check 
} from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function BuildPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [previewCode, setPreviewCode] = useState("");
  const [projectTree, setProjectTree] = useState({ routes: [], components: [] });
  const [messages, setMessages] = useState<any[]>(() => {
    const saved = sessionStorage.getItem("genesys_v2");
    return saved ? JSON.parse(saved) : [];
  });
  const scrollRef = useRef<HTMLDivElement>(null);

  const refreshFiles = async () => {
    try {
      const res = await fetch('http://127.0.0.1:5000/list-files');
      const data = await res.json();
      if(data.tree) setProjectTree(data.tree);
    } catch (e) { console.error("Explorer offline"); }
  };

  useEffect(() => { 
    refreshFiles();
  }, []);

  useEffect(() => {
    sessionStorage.setItem("genesys_v2", JSON.stringify(messages));
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, loading]);

  async function handleSend(override?: string) {
    const promptText = override || input;
    if (!promptText.trim() || loading) return;
    
    setLoading(true);
    if(!override) {
        setMessages(prev => [...prev, { role: "user", text: promptText }]);
        setInput("");
    }

    try {
      // 1. Contact the AI Council
      const response = await askGenesys(promptText);
      const text = response.text;

      // 2. SURGICAL PREVIEW EXTRACTION (Vanilla JS Fix)
      const previewMatch = text.match(/<GENESYS_PREVIEW>([\s\S]*?)(?:<\/GENESYS_PREVIEW>|$)/i);
      if (previewMatch && previewMatch[1]) {
        const rawContent = previewMatch[1].trim();
        
        // Wrap in a high-end Vanilla Sandbox to prevent SVG/React errors
        setPreviewCode(`
          <!DOCTYPE html>
          <html>
            <head>
              <script src="https://cdn.tailwindcss.com"></script>
              <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;700&display=swap" rel="stylesheet">
              <style>
                body { background:#000; color:#fff; font-family:'Sora',sans-serif; margin:0; padding:20px; min-height:100vh; display:flex; justify-content:center; align-items:center; }
                canvas, svg { box-shadow: 0 0 80px rgba(0, 217, 255, 0.1); border: 1px solid #222; border-radius: 12px; max-width: 100%; }
              </style>
            </head>
            <body>
              <div id="root" class="w-full max-w-4xl">${rawContent}</div>
              <script>
                window.focus();
                window.onerror = function(m,u,l){ parent.postMessage({type:'SYSTEM_CRASH',error:m,line:l},'*'); };
              </script>
            </body>
          </html>
        `);
      }

      // 3. FILE BRIDGE (Writing to Disk)
      const fileRegex = /---FILE:?\s*([\w\.\/]+)\s*---[\s\S]*?\[CODE START\]([\s\S]*?)(?:\[CODE END\]|$)/gi;
      let fMatch;
      let filesUpdated = 0;
      while ((fMatch = fileRegex.exec(text)) !== null) {
        filesUpdated++;
        await fetch('http://127.0.0.1:5000/write-file', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: fMatch[1].trim(), code: fMatch[2].trim() })
        });
      }
      if (filesUpdated > 0) refreshFiles();

      // 4. CLEAN CHAT UI
      const cleanDisplay = text
        .replace(/<THOUGHT>[\s\S]*?<\/THOUGHT>/gi, "")
        .replace(/<PLAN>[\s\S]*?<\/PLAN>/gi, "")
        .replace(/<GENESYS_PREVIEW>[\s\S]*?(?:<\/GENESYS_PREVIEW>|$)/gi, "")
        .replace(/---FILE:[\s\S]*?\[CODE END\]/gi, "")
        .trim();

      setMessages(prev => [...prev, { 
        role: "bot", 
        text: cleanDisplay || "Architectural sync complete.", 
        thought: text.match(/<THOUGHT>([\s\S]*?)<\/THOUGHT>/i)?.[1],
        plan: text.match(/<PLAN>([\s\S]*?)<\/PLAN>/i)?.[1],
        agent: response.agent,
        hasFile: filesUpdated > 0
      }]);

    } catch (err: any) {
      console.error("System Error:", err);
      setMessages(prev => [...prev, { role: "bot", text: "❌ Connection Error: " + err.message, agent: "System" }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-[#020202] text-white overflow-hidden font-sans">
      <Navbar />
      <div className="flex flex-1 pt-16 overflow-hidden">
        
        {/* COLUMN 1: EXPLORER */}
        <aside className="w-56 shrink-0 border-r border-white/5 bg-zinc-950/80 p-4 hidden md:flex flex-col overflow-y-auto">
          <div className="flex items-center justify-between mb-6 opacity-40">
             <span className="text-[9px] font-black uppercase tracking-[0.3em]">Project Explorer</span>
             <RefreshCw size={12} onClick={refreshFiles} className="cursor-pointer hover:rotate-180 transition-all"/>
          </div>
          <div className="space-y-4">
            <div>
              <h4 className="text-[8px] font-bold text-blue-400/40 uppercase mb-2 tracking-widest px-2">Routes</h4>
              {projectTree.routes.map(f => <div key={f} className="text-[10px] text-white/30 p-1.5 rounded truncate font-mono flex items-center gap-2">📄 {f}</div>)}
            </div>
            <div>
              <h4 className="text-[8px] font-bold text-blue-400/40 uppercase mb-2 tracking-widest px-2">Components</h4>
              {projectTree.components.map(f => <div key={f} className="text-[10px] text-white/30 p-1.5 rounded truncate font-mono flex items-center gap-2">🧩 {f}</div>)}
            </div>
          </div>
        </aside>

        {/* COLUMN 2: CHAT */}
        <aside className="w-[420px] shrink-0 border-r border-white/5 flex flex-col bg-zinc-950/40 backdrop-blur-xl">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-6">
            {messages.map((m, i) => (
              <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                {m.agent && <div className="text-[9px] font-bold text-blue-400/50 uppercase tracking-widest mb-2">{m.agent}</div>}
                
                {m.thought && (
                  <div className="mb-2 p-3 bg-blue-500/5 border border-blue-500/10 rounded-xl text-[10px] text-blue-300 italic w-full leading-relaxed">💭 {m.thought}</div>
                )}
                
                {m.plan && (
                    <div className="mb-2 p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-xl text-[10px] text-emerald-400 w-full"><ReactMarkdown>{m.plan}</ReactMarkdown></div>
                )}

                <div className={`p-4 rounded-2xl text-sm ${m.role === 'user' ? 'bg-blue-600 shadow-xl shadow-blue-900/20' : 'bg-zinc-900 border border-white/5'}`}>
                   <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
                </div>

                {m.role === 'bot' && m.hasFile && (
                  <div className="flex items-center gap-1 mt-2 text-[8px] font-black text-green-500/40 bg-green-500/5 px-2 py-0.5 rounded-full border border-green-500/10 uppercase tracking-widest">
                     <Check size={8}/> Disk_Synced
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="p-4 bg-black/40 border-t border-white/5">
            <div className="flex items-end gap-2 bg-zinc-900 border border-white/10 rounded-2xl p-2">
              <textarea 
                value={input} 
                onChange={e => setInput(e.target.value)} 
                onKeyDown={e => {if(e.key==='Enter' && !e.shiftKey){e.preventDefault(); handleSend();}}}
                placeholder="Describe vision..."
                className="flex-1 bg-transparent border-none outline-none text-sm p-2 resize-none max-h-32 text-white"
                rows={1}
              />
              <button onClick={() => handleSend()} className="bg-blue-600 p-2.5 rounded-xl shadow-lg hover:bg-blue-500 transition-all"><Send size={18}/></button>
            </div>
          </div>
        </aside>

        {/* COLUMN 3: WORKSPACE */}
        <div className="flex-1 p-6 relative">
          <div className="w-full h-full rounded-[2.5rem] overflow-hidden border border-white/5 bg-black shadow-2xl relative">
            {previewCode ? (
              <iframe srcDoc={previewCode} className="w-full h-full border-none" sandbox="allow-scripts" />
            ) : <div className="w-full h-full flex items-center justify-center text-white/5 italic">Awaiting Architectural Signal</div>}
            <SelfHealer previewCode={previewCode} onRepair={(p) => handleSend(p)} isBusy={loading} />
          </div>
        </div>
      </div>
    </div>
  );
}

export const Route = createRoute({ getParentRoute: () => rootRoute, path: "/build", component: BuildPage });