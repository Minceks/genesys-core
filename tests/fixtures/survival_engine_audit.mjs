import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const {createGame,LEVELS}=await import(pathToFileURL(process.argv[2]));
let now=0,id=0,queue=new Map();
const ctx=new Proxy({},{get(t,k){if(k==='createRadialGradient')return ()=>({addColorStop(){}});return k in t?t[k]:()=>{}},set(t,k,v){t[k]=v;return true}});
const makeCanvas=()=>({width:1200,height:760,getContext:()=>ctx,getBoundingClientRect:()=>({width:1200,height:760,left:0,top:0})});
globalThis.document={createElement:()=>makeCanvas()};globalThis.window={devicePixelRatio:1};globalThis.requestAnimationFrame=f=>{queue.set(++id,f);return id};globalThis.cancelAnimationFrame=i=>queue.delete(i);
function tick(){now+=40;const entries=[...queue.values()];queue.clear();for(const f of entries)f(now)}
const results=[];
for(let level=0;level<LEVELS.length;level++){
 let won=false;
 for(let strategy=0;strategy<4&&!won;strategy++){
  let mode,hud,completed;const game=createGame(makeCanvas(),{onMode:v=>mode=v,onHUD:v=>hud=v,onComplete:v=>completed=v});
  game.start(level);
  let ticks=0;for(let i=0;i<3500&&['playing','upgrade'].includes(mode);i++){ticks=i;
   if(mode==='upgrade')game.chooseUpgrade('rapid');
   if(strategy>0){game.dash();game.pulse()}
   const dirs=[[1,0],[0,1],[-1,0],[0,-1]],dir=dirs[(Math.floor(i/(strategy===1?35:strategy===2?95:65))+strategy)%4];
   game.setInput({fire:true,x:strategy===0?0:dir[0],y:strategy===0?0:dir[1]});tick();
  }
  if(mode==='cleared'){assert(completed.score>0&&completed.kills===LEVELS[level].waves.reduce((a,b)=>a+b,0));won=true;results.push({level:level+1,won:true,health:hud.health,kills:completed.kills,strategy,seconds:Math.round(ticks*.04)})}
  game.destroy();assert.equal(queue.size,0);
 }
 assert(won,'Level '+(level+1)+' must be completable with ordinary movement and firing');
}
console.log(JSON.stringify({allSectorsCompletable:true,checks:results}));

let mode,latest;
const g=createGame(makeCanvas(),{onMode:v=>mode=v,onHUD:v=>latest=v});
g.start(0);g.dash();assert(latest.dashCooldown>0);g.pause();const cooldown=latest.dashCooldown;for(let i=0;i<30;i++)tick();assert.equal(latest.dashCooldown,cooldown);g.resume();for(let i=0;i<25;i++)tick();assert(latest.dashCooldown<cooldown);
g.restart();for(let i=0;i<2000&&mode==='playing'&&latest.health===5;i++)tick();assert(latest.health<5);const beforeKills=latest.kills;g.pulse();assert(latest.pulseCooldown>0&&latest.kills>beforeKills,'Pulse must deal real damage and eliminate nearby walkers');const killsAfter=latest.kills;g.pulse();assert.equal(latest.kills,killsAfter,'Pulse cooldown prevents repeated damage');
g.start(0);for(let i=0;i<2500&&mode==='playing';i++){g.setInput({fire:true});tick()}assert.equal(mode,'upgrade');g.chooseUpgrade('medic');assert.equal(latest.maxHealth,6);assert.equal(latest.health,6);g.restart();assert.equal(latest.maxHealth,5);
for(let i=0;i<2500&&mode==='playing';i++){g.setInput({fire:true});tick()}assert.equal(mode,'upgrade');g.chooseUpgrade('pulse');assert.equal(latest.pulsePower,3);
g.start(0);for(let i=0;i<2500&&['playing','upgrade'].includes(mode);i++){if(mode==='upgrade')g.chooseUpgrade('rapid');g.setInput({fire:true});tick()}assert.equal(mode,'cleared');const fire=latest.fireMultiplier;g.next();assert.equal(latest.level,2);assert.equal(latest.fireMultiplier,fire);g.restart();assert.equal(latest.fireMultiplier,fire);
g.start(0);for(let i=0;i<2000&&mode==='playing';i++)tick();assert.equal(mode,'dead');assert.equal(latest.kills,0);g.restart();assert.equal(mode,'playing');assert.equal(latest.health,5);assert.equal(queue.size,1);g.destroy();assert.equal(queue.size,0);
console.log(JSON.stringify({dashCooldownAndPause:true,pulseDealsDamage:true,pulseCooldown:true,medicUpgrade:true,pulseUpgrade:true,buildCarriesAcrossSectors:true,retryResetsEntryLoadout:true,passiveCollisionCannotWin:true,lossAndRetry:true,singleSimulation:true}));

let damageTimes=[],contactHud,contactMode;const h=createGame(makeCanvas(),{onHUD:v=>contactHud=v,onMode:v=>contactMode=v,onEvent:e=>{if(e==='hurt')damageTimes.push(now)}});h.start(0);for(let i=0;i<3000&&contactMode==='playing';i++)tick();assert.equal(contactMode,'dead');assert.equal(damageTimes.length,5);for(let i=1;i<damageTimes.length;i++)assert(damageTimes[i]-damageTimes[i-1]>=850,'Contact damage must respect the 850ms recovery window');h.destroy();assert.equal(queue.size,0);console.log(JSON.stringify({fairDamageIntervals:damageTimes.slice(1).map((t,i)=>t-damageTimes[i]),noPerFrameDamage:true}));
