import { Groq } from "groq-sdk";

const apiKey = import.meta.env.VITE_GROQ_API_KEY;
const groq = new Groq({ apiKey, dangerouslyAllowBrowser: true });

// The Council of Agents
const AGENT_COUNCIL = [
  { id: "openai/gpt-oss-120b", role: "Lead Architect" },
  { id: "qwen/qwen3.8-27b", role: "Logic Specialist" },
  { id: "openai/gpt-oss-20b", role: "Speed Specialist" }
];

export async function askGenesys(prompt: string) {
  let projectMap = "No context.";
  let roadmap = "No roadmap.";

  try {
    // 1. GATHER CONTEXT (Using the same names as Python)
    const [treeRes, roadmapRes] = await Promise.all([
      fetch('http://127.0.0.1:5000/list-files'),
      fetch('http://127.0.0.1:5000/read-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: 'roadmap.md' })
      })
    ]);
    
    const treeData = await treeRes.json();
    const roadmapData = await roadmapRes.json();
    
    projectMap = JSON.stringify(treeData.tree);
    roadmap = roadmapData.content || "Empty roadmap.";
  } catch (e) {
    console.warn("⚠️ Bridge context offline. AI is running in blind mode.");
  }

  // 2. THE CTO BRAIN
  for (const agent of AGENT_COUNCIL) {
    try {
      const completion = await groq.chat.completions.create({
        messages: [
          { 
            role: "system", 
            content: `You are the GENESYS-CHIEF-ARCHITECT. 

STRICT ARCHITECTURAL SEPARATION:
1. <GENESYS_PREVIEW>: STANDALONE VANILLA HTML/JS ONLY.
   - NO React hooks (useState/useEffect).
   - NO JSX curly braces in attributes (e.g., use x="20" NOT x={20}).
   - Everything must be hard-coded or calculated via Vanilla JS.

2. ---FILE---: FULL PRODUCTION REACT/TSX.
   - Use @tanstack/react-router.
   - Use Recharts/Lucide as needed.

3. REUSABILITY:
   - When building complex suites, put reusable logic in 'src/components/ui/'.

If you put React syntax {} in the <GENESYS_PREVIEW> block, the simulation will explode.`
          },
          { role: "user", content: prompt }
        ],
        model: agent.id,
      });

      return { text: completion.choices[0]?.message?.content || "", agent: agent.role };
    } catch (e) { continue; }
  }
  return { text: "Council offline.", agent: "Error" };
}