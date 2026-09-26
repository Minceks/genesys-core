import { createRoute } from "@tanstack/react-router";
import { Route as rootRoute } from "./__root";
import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Navbar } from "@/components/genesys/navbar";
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  Title, 
  Tooltip, 
  Legend,
  Filler
} from 'chart.js';
import { Line } from "react-chartjs-2";
import { Activity, Cpu, Database, Zap, ShieldCheck } from "lucide-react";

// 1. Register ChartJS components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

// 2. Define the Route
export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/dashboard",
  component: DashboardPage,
});

// 3. The Main Component
function DashboardPage() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['neural-telemetry'],
    queryFn: async () => {
      // Simulated real-time AI node data
      return {
        activeNodes: 1284,
        throughput: (Math.random() * 50 + 40).toFixed(1),
        securityLevel: "Level 5",
        uptime: "99.99%",
        dataPoints: [45, 52, 48, 70, 65, 58, 72]
      };
    },
    refetchInterval: 3000 // Refreshes every 3 seconds
  });

  const chartData = {
    labels: ['T-60', 'T-50', 'T-40', 'T-30', 'T-20', 'T-10', 'Now'],
    datasets: [{
      label: 'Synaptic Load',
      data: metrics?.dataPoints || [],
      borderColor: '#00d9ff',
      backgroundColor: 'rgba(0, 217, 255, 0.05)',
      fill: true,
      tension: 0.4,
      pointRadius: 0,
    }]
  };

  if (isLoading) {
    return (
      <div className="h-screen bg-black flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="animate-spin text-blue-500" size={40} />
          <p className="text-blue-400 font-mono text-xs uppercase tracking-widest">Establishing Neural Link...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020202] text-white font-sans selection:bg-blue-500/30">
      <Navbar />
      
      <main className="pt-28 pb-12 px-8 max-w-7xl mx-auto">
        {/* Header Section */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-12">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="h-2 w-2 rounded-full bg-blue-500 animate-ping" />
              <span className="text-[10px] font-black uppercase tracking-[0.3em] text-blue-500/60">Live Environment</span>
            </div>
            <h1 className="text-5xl font-bold tracking-tighter" style={{ fontFamily: 'Sora' }}>
              Neural <span className="text-blue-500">Oversight</span>
            </h1>
          </div>
          
          <div className="flex gap-4">
            <div className="px-4 py-2 bg-white/5 border border-white/10 rounded-2xl flex items-center gap-3">
              <ShieldCheck size={16} className="text-emerald-500" />
              <div className="text-left">
                <p className="text-[8px] font-bold text-white/30 uppercase tracking-widest leading-none">Security</p>
                <p className="text-xs font-mono text-emerald-500">{metrics?.securityLevel}</p>
              </div>
            </div>
          </div>
        </header>

        {/* Real-time Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {[
            { label: "Active Nodes", value: metrics?.activeNodes, icon: Cpu, trend: "+12.4%" },
            { label: "Neural Throughput", value: metrics?.throughput + " Gops", icon: Activity, trend: "Stable" },
            { label: "Core Uptime", value: metrics?.uptime, icon: Database, trend: "Optimal" }
          ].map((stat, idx) => (
            <div key={idx} className="p-8 rounded-[2.5rem] bg-zinc-900/40 border border-white/5 backdrop-blur-xl group hover:border-blue-500/30 transition-all shadow-2xl">
              <stat.icon className="text-blue-400 mb-6 group-hover:scale-110 transition-transform" size={28} />
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/20 mb-1">{stat.label}</p>
              <div className="flex items-baseline justify-between">
                <h3 className="text-4xl font-mono tracking-tight">{stat.value}</h3>
                <span className="text-[10px] font-bold text-blue-500/40">{stat.trend}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Telemetry Chart Area */}
        <div className="p-10 rounded-[3rem] bg-zinc-900/20 border border-white/5 backdrop-blur-md relative h-96 shadow-2xl overflow-hidden">
          <div className="absolute top-8 left-10 flex items-center gap-2">
            <Zap size={14} className="text-blue-500" />
            <span className="text-xs font-bold uppercase tracking-widest text-white/40">Neural Frequency Telemetry</span>
          </div>
          <Line 
            data={chartData} 
            options={{ 
              responsive: true, 
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: {
                y: { display: false },
                x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: 'rgba(255,255,255,0.2)', font: { size: 10 } } }
              }
            }} 
          />
        </div>
      </main>
    </div>
  );
}