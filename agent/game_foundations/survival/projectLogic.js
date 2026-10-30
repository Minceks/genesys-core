import { GAME_DESIGN } from "./gameDesign.js";
export const LEVELS = GAME_DESIGN.levels;
const W = 1200,
  H = 760,
  TAU = Math.PI * 2;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
function rng(seed) {
  return () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}
export function createGame(
  canvas,
  {
    onHUD = () => {},
    onMode = () => {},
    onComplete = () => {},
    onEvent = () => {},
  } = {},
) {
  const ctx = canvas.getContext("2d");
  let frame = 0,
    last = 0,
    destroyed = false,
    mode = "menu",
    worldTime = 0,
    reduced = false;
  let level = LEVELS[0],
    wave = 0,
    score = 0,
    kills = 0,
    enemies = [],
    bullets = [],
    particles = [],
    stains = [],
    spawn = [],
    elapsed = 0,
    cooldown = 0,
    flash = 0,
    shake = 0,
    hudTick = 0,
    waveDelay = 0;
  let loadout = {
      fireMultiplier: 1,
      maxHealth: 5,
      pulsePower: 2,
      pulseRadius: 160,
    },
    entry = null,
    dashCooldown = 0,
    dashTime = 0,
    dashVector = { x: 0, y: 0 },
    pulseCooldown = 0,
    pulseFlash = 0;
  let player = {
    x: 600,
    y: 410,
    hp: loadout.maxHealth,
    angle: -Math.PI / 2,
    inv: 0,
  };
  const input = { x: 0, y: 0, fire: false, aim: null };
  let view = { x: 0, y: 0, z: 1 },
    background = null,
    blocks = [];
  const rectangle = (c, x, y, w, h, r = 0) => {
    c.beginPath();
    if (typeof c.roundRect === "function") c.roundRect(x, y, w, h, r);
    else c.rect(x, y, w, h);
    c.fill();
  };
  const modeTo = (value) => {
    mode = value;
    onMode(value);
    input.fire = false;
    input.x = 0;
    input.y = 0;
  };
  function hud() {
    onHUD({
      level: level.id,
      wave: wave + 1,
      waves: level.waves.length,
      score,
      kills,
      health: player.hp,
      maxHealth: loadout.maxHealth,
      dashCooldown,
      pulseCooldown,
      fireMultiplier: loadout.fireMultiplier,
      pulsePower: loadout.pulsePower,
      pulseRadius: loadout.pulseRadius,
      enemies: enemies.length + spawn.length,
      mode,
      intermission: waveDelay > 0,
    });
  }
  function makeBackground() {
    blocks =
      level.layout % 2 === 0
        ? [
            { x: 95, y: 95, w: 265, h: 145, kind: "building" },
            { x: 865, y: 505, w: 240, h: 150, kind: "building" },
            { x: 385, y: 520, w: 98, h: 62, kind: "crate" },
            { x: 770, y: 215, w: 120, h: 58, kind: "crate" },
            { x: 860, y: 95, w: 165, h: 82, kind: "car" },
          ]
        : [
            { x: 85, y: 490, w: 270, h: 170, kind: "building" },
            { x: 900, y: 90, w: 215, h: 160, kind: "building" },
            { x: 250, y: 155, w: 175, h: 78, kind: "car" },
            { x: 760, y: 520, w: 100, h: 65, kind: "crate" },
            { x: 700, y: 150, w: 120, h: 58, kind: "crate" },
          ];
    background = document.createElement("canvas");
    background.width = W;
    background.height = H;
    const c = background.getContext("2d"),
      random = rng(834 + level.id * 31);
    c.fillStyle = GAME_DESIGN.colors.ground[
      level.layout
    ];
    c.fillRect(0, 0, W, H);
    c.strokeStyle = "#ffffff08";
    c.lineWidth = 1;
    for (let x = 0; x < W; x += 48) {
      c.beginPath();
      c.moveTo(x, 0);
      c.lineTo(x, H);
      c.stroke();
    }
    for (let y = 0; y < H; y += 48) {
      c.beginPath();
      c.moveTo(0, y);
      c.lineTo(W, y);
      c.stroke();
    }
    for (let i = 0; i < 2100; i++) {
      c.fillStyle = i % 3 ? "#b6c5ab0a" : "#00000026";
      c.fillRect(
        random() * W,
        random() * H,
        random() * 4 + 1,
        random() * 2 + 1,
      );
    }
    c.save();
    c.translate(600, 380);
    c.rotate(-0.12);
    c.strokeStyle = "#cfbd6e29";
    c.setLineDash([22, 16]);
    c.strokeRect(-225, -150, 450, 300);
    c.setLineDash([]);
    c.fillStyle = "#c7c6a51c";
    c.font = "bold 32px monospace";
    c.textAlign = "center";
    c.fillText(level.id === 5 ? "EXTRACTION ZONE" : "KEEP CLEAR", 0, 12);
    c.restore();
    for (let i = 0; i < 16; i++) {
      const x = random() * W,
        y = random() * H;
      c.strokeStyle = "#00000045";
      c.beginPath();
      c.moveTo(x, y);
      c.lineTo(x + random() * 40, y + random() * 14);
      c.lineTo(x + random() * 60, y - 8);
      c.stroke();
    }
    for (let i = 0; i < 70; i++) {
      const x = 80 + random() * (W - 160),
        y = 80 + random() * (H - 160);
      c.save();
      c.translate(x, y);
      c.rotate(random() * TAU);
      c.fillStyle = i % 4 === 0 ? "#9b997c35" : "#070e0b55";
      c.fillRect(-3, -1, 5 + random() * 9, 2 + random() * 4);
      c.restore();
    }
    c.strokeStyle = "#8a9d7430";
    c.lineWidth = 2;
    c.beginPath();
    c.arc(620, 330, 29, 0, TAU);
    c.stroke();
    c.fillStyle = "#0a1712";
    c.beginPath();
    c.arc(620, 330, 23, 0, TAU);
    c.fill();
    c.strokeStyle = "#52674e";
    for (let i = -12; i < 15; i += 6) {
      c.beginPath();
      c.moveTo(602, 330 + i);
      c.lineTo(638, 330 + i);
      c.stroke();
    }
    const beacon = c.createRadialGradient(620, 330, 2, 620, 330, 130);
    beacon.addColorStop(0, "#b8d99422");
    beacon.addColorStop(1, "#b8d99400");
    c.fillStyle = beacon;
    c.fillRect(490, 200, 260, 260);
    for (const b of blocks) {
      c.fillStyle = "#00000066";
      rectangle(c, b.x + 15, b.y + 20, b.w, b.h, 4);
      if (b.kind === "building") {
        c.fillStyle = "#0c1515";
        rectangle(c, b.x - 5, b.y - 5, b.w + 10, b.h + 10, 3);
        c.fillStyle = "#35413b";
        rectangle(c, b.x, b.y, b.w, b.h, 2);
        c.fillStyle = "#45534a";
        c.fillRect(b.x, b.y, b.w, 9);
        c.fillStyle = "#1a2723";
        c.fillRect(b.x + 12, b.y + 20, b.w - 24, b.h - 32);
        c.strokeStyle = "#71816a25";
        for (let y = b.y + 25; y < b.y + b.h - 15; y += 14) {
          c.beginPath();
          c.moveTo(b.x + 15, y);
          c.lineTo(b.x + b.w - 15, y);
          c.stroke();
        }
        c.fillStyle = "#54614e";
        rectangle(c, b.x + b.w - 70, b.y + 30, 44, 42, 2);
        c.strokeStyle = "#16211d";
        for (let y = 0; y < 5; y++) {
          c.beginPath();
          c.moveTo(b.x + b.w - 66, b.y + 36 + y * 6);
          c.lineTo(b.x + b.w - 30, b.y + 36 + y * 6);
          c.stroke();
        }
        c.fillStyle = "#b8c990";
        for (let x = b.x + 25; x < b.x + b.w - 20; x += 55) {
          c.fillRect(x, b.y + b.h - 4, 24, 4);
          const light = c.createRadialGradient(
            x + 12,
            b.y + b.h,
            0,
            x + 12,
            b.y + b.h,
            75,
          );
          light.addColorStop(0, "#e9ce791f");
          light.addColorStop(1, "#e9ce7900");
          c.fillStyle = light;
          c.fillRect(x - 63, b.y + b.h - 30, 150, 105);
          c.fillStyle = "#b8c990";
        }
      } else if (b.kind === "car") {
        c.fillStyle = "#535b4c";
        rectangle(c, b.x, b.y, b.w, b.h, 14);
        c.fillStyle = "#242f2c";
        rectangle(c, b.x + 42, b.y + 8, b.w - 75, b.h - 16, 8);
        c.fillStyle = "#73918b50";
        c.fillRect(b.x + 44, b.y + 12, 17, b.h - 24);
        c.fillRect(b.x + b.w - 54, b.y + 12, 15, b.h - 24);
        c.fillStyle = "#171e1a";
        for (const xx of [b.x + 24, b.x + b.w - 35])
          for (const yy of [b.y - 5, b.y + b.h - 7])
            rectangle(c, xx, yy, 26, 12, 3);
        c.fillStyle = "#e8dfb87a";
        c.fillRect(b.x + b.w - 4, b.y + 14, 3, 13);
        c.fillRect(b.x + b.w - 4, b.y + b.h - 27, 3, 13);
      } else {
        c.fillStyle = "#70634b";
        rectangle(c, b.x, b.y, b.w, b.h, 3);
        c.strokeStyle = "#3f3a2d";
        c.lineWidth = 5;
        c.strokeRect(b.x + 6, b.y + 6, b.w - 12, b.h - 12);
        c.beginPath();
        c.moveTo(b.x + 8, b.y + 8);
        c.lineTo(b.x + b.w - 8, b.y + b.h - 8);
        c.moveTo(b.x + b.w - 8, b.y + 8);
        c.lineTo(b.x + 8, b.y + b.h - 8);
        c.stroke();
        c.fillStyle = "#a294641f";
        c.fillRect(b.x, b.y, b.w, 5);
      }
    }
    c.strokeStyle = "#77877930";
    c.lineWidth = 2;
    for (const y of [26, H - 26]) {
      c.beginPath();
      c.moveTo(0, y);
      c.lineTo(W, y);
      c.stroke();
      for (let x = 20; x < W; x += 28) {
        c.beginPath();
        c.moveTo(x, y - 14);
        c.lineTo(x + 20, y + 14);
        c.stroke();
      }
    }
    c.fillStyle = "#b3bf8e55";
    for (const [x, y] of [
      [45, 45],
      [W - 45, 45],
      [45, H - 45],
      [W - 45, H - 45],
    ]) {
      c.fillRect(x - 3, y - 14, 6, 28);
      const g = c.createRadialGradient(x, y, 0, x, y, 210);
      g.addColorStop(0, "#dfe2af13");
      g.addColorStop(1, "#dfe2af00");
      c.fillStyle = g;
      c.fillRect(x - 210, y - 210, 420, 420);
      c.fillStyle = "#b3bf8e55";
    }
  }
  function reset(index, carry = false) {
    if (!carry) {
      loadout = {
        fireMultiplier: 1,
        maxHealth: 5,
        pulsePower: 2,
        pulseRadius: 160,
      };
      score = 0;
      kills = 0;
    }
    entry = { loadout: { ...loadout }, score, kills };
    dashCooldown = 0;
    dashTime = 0;
    pulseCooldown = 0;
    pulseFlash = 0;
    level = LEVELS[clamp(index, 0, LEVELS.length - 1)];
    wave = 0;
    elapsed = 0;
    player = {
      x: 600,
      y: 410,
      hp: loadout.maxHealth,
      angle: -Math.PI / 2,
      inv: 0,
    };
    bullets = [];
    particles = [];
    stains = [];
    shake = 0;
    flash = 0;
    waveDelay = 0;
    makeBackground();
    spawnWave();
  }
  function spawnWave() {
    enemies = [];
    spawn = [];
    cooldown = 0;
    const random = rng(level.id * 731 + wave * 91 + 18),
      count = level.waves[wave];
    for (let i = 0; i < count; i++) {
      const side = i % 4;
      let x = side === 0 ? 45 : side === 1 ? W - 45 : 70 + random() * (W - 140),
        y = side === 2 ? 45 : side === 3 ? H - 45 : 70 + random() * (H - 140);
      const brute = level.id >= 4 && i % 4 === 0,
        runner = level.id >= 3 && i % 3 === 0 && !brute;
      spawn.push({
        x,
        y,
        delay: Math.floor(i / 3) * 0.32,
        telegraph: 0,
        kind: brute ? "brute" : runner ? "runner" : "walker",
        hp: brute
          ? level.id + 2
          : runner
            ? 2
            : 2 + Math.floor((level.id - 1) / 2),
        maxHp: brute
          ? level.id + 2
          : runner
            ? 2
            : 2 + Math.floor((level.id - 1) / 2),
        radius: brute ? 21 : 14,
        speed: level.speed * (brute ? 0.7 : runner ? 1.65 : 1),
        seed: random() * 10,
        angle: 0,
        hit: 0,
      });
    }
    hud();
  }
  function start(index, carry = false, entryWave = 0) {
    reset(index, carry);
    if (entryWave > 0) { wave = Math.min(level.waves.length - 1, entryWave); spawnWave(); }
    modeTo("playing");
    hud();
    onEvent("start");
  }
  function pause() {
    if (mode === "playing") {
      modeTo("paused");
      hud();
    }
  }
  function resume() {
    if (mode === "paused") {
      modeTo("playing");
      hud();
    }
  }
  function menu() {
    reset(0);
    modeTo("menu");
    hud();
  }
  function restart() {
    loadout = { ...entry.loadout };
    score = entry.score;
    kills = entry.kills;
    start(level.id - 1, true);
  }
  function next() {
    if (level.id < LEVELS.length) start(level.id, true);
    else {
      modeTo("victory");
      hud();
    }
  }
  function chooseUpgrade(type) {
    if (mode !== "upgrade" || !["rapid", "medic", "pulse"].includes(type))
      return;
    if (type === "rapid")
      loadout.fireMultiplier = Math.max(0.25, loadout.fireMultiplier * 0.8);
    if (type === "medic") {
      loadout.maxHealth = Math.min(8, loadout.maxHealth + 1);
      player.hp = Math.min(loadout.maxHealth, player.hp + 2);
    }
    if (type === "pulse") {
      loadout.pulsePower++;
      loadout.pulseRadius = Math.min(250, loadout.pulseRadius + 30);
    }
    wave++;
    spawnWave();
    modeTo("playing");
    hud();
    onEvent("upgrade");
  }
  function dash() {
    if (mode !== "playing" || dashCooldown > 0) return;
    const len = Math.hypot(input.x, input.y);
    dashVector =
      len > 0.1
        ? { x: input.x / len, y: input.y / len }
        : { x: Math.cos(player.angle), y: Math.sin(player.angle) };
    dashCooldown = GAME_DESIGN.balance.dashCooldown;
    dashTime = 0.18;
    player.inv = Math.max(player.inv, 0.3);
    burst(player.x, player.y, "#a8d5c1", 6);
    hud();
    onEvent("dash");
  }
  function pulse() {
    if (mode !== "playing" || pulseCooldown > 0) return;
    pulseCooldown = GAME_DESIGN.balance.pulseCooldown;
    pulseFlash = 0.6;
    for (let i = enemies.length - 1; i >= 0; i--) {
      const e = enemies[i],
        dx = e.x - player.x,
        dy = e.y - player.y,
        len = Math.hypot(dx, dy) || 1;
      if (len > loadout.pulseRadius) continue;
      e.hp -= loadout.pulsePower;
      e.hit = 0.15;
      move(e, (dx / len) * 55, (dy / len) * 55, e.radius);
      burst(e.x, e.y, "#c8e2c4", 5);
      if (e.hp <= 0) {
        score += e.kind === "brute" ? 250 : e.kind === "runner" ? 150 : 100;
        kills++;
        stains.push({ x: e.x, y: e.y, a: e.angle });
        enemies.splice(i, 1);
        onEvent("kill");
      }
    }
    hud();
    onEvent("pulse");
  }
  function setInput(patch) {
    Object.assign(input, patch);
  }
  function move(body, dx, dy, r) {
    body.x = clamp(body.x + dx, r + 32, W - r - 32);
    for (const b of blocks)
      if (
        body.y > b.y - r &&
        body.y < b.y + b.h + r &&
        body.x > b.x - r &&
        body.x < b.x + b.w + r
      )
        body.x = dx > 0 ? b.x - r : b.x + b.w + r;
    body.y = clamp(body.y + dy, r + 32, H - r - 32);
    for (const b of blocks)
      if (
        body.x > b.x - r &&
        body.x < b.x + b.w + r &&
        body.y > b.y - r &&
        body.y < b.y + b.h + r
      )
        body.y = dy > 0 ? b.y - r : b.y + b.h + r;
  }
  function burst(x, y, color, count = 9) {
    if (reduced) count = Math.min(count, 2);
    for (let i = 0; i < count; i++) {
      const a = (i / count) * TAU + elapsed;
      particles.push({
        x,
        y,
        vx: Math.cos(a) * (30 + i * 7),
        vy: Math.sin(a) * (30 + i * 7),
        life: 0.22 + i * 0.028,
        max: 0.22 + i * 0.028,
        color,
      });
    }
  }
  function step(dt) {
    elapsed += dt;
    worldTime += dt;
    cooldown -= dt;
    dashCooldown = Math.max(0, dashCooldown - dt);
    dashTime = Math.max(0, dashTime - dt);
    pulseCooldown = Math.max(0, pulseCooldown - dt);
    pulseFlash = Math.max(0, pulseFlash - dt);
    flash = Math.max(0, flash - dt);
    shake = Math.max(0, shake - dt * 20);
    player.inv = Math.max(0, player.inv - dt);
    if (waveDelay > 0) {
      waveDelay -= dt;
      if (waveDelay <= 0) {
        wave++;
        spawnWave();
      }
      return;
    }
    const len = Math.hypot(input.x, input.y) || 1;
    move(
      player,
      (input.x / Math.max(1, len)) * 185 * dt,
      (input.y / Math.max(1, len)) * 185 * dt,
      15,
    );
    if (dashTime > 0)
      move(player, dashVector.x * 560 * dt, dashVector.y * 560 * dt, 15);
    for (const e of spawn) e.delay -= dt;
    for (let i = spawn.length - 1; i >= 0; i--)
      if (spawn[i].delay <= -0.65) {
        enemies.push(spawn[i]);
        spawn.splice(i, 1);
      }
    const nearest = [...enemies].sort(
      (a, b) =>
        Math.hypot(a.x - player.x, a.y - player.y) -
        Math.hypot(b.x - player.x, b.y - player.y),
    )[0];
    const aim = input.aim || nearest;
    if (aim) player.angle = Math.atan2(aim.y - player.y, aim.x - player.x);
    if (input.fire && cooldown <= 0) {
      cooldown = 0.24 * loadout.fireMultiplier;
      flash = 0.055;
      bullets.push({
        x: player.x + Math.cos(player.angle) * 27,
        y: player.y + Math.sin(player.angle) * 27,
        vx: Math.cos(player.angle) * 760,
        vy: Math.sin(player.angle) * 760,
        life: 0.8,
      });
      onEvent("shot");
    }
    for (const e of enemies) {
      e.hit = Math.max(0, e.hit - dt);
      e.angle = Math.atan2(player.y - e.y, player.x - e.x);
      move(
        e,
        Math.cos(e.angle) * e.speed * dt,
        Math.sin(e.angle) * e.speed * dt,
        e.radius,
      );
      if (
        Math.hypot(e.x - player.x, e.y - player.y) < e.radius + 13 &&
        player.inv <= 0
      ) {
        player.hp--;
        player.inv = 0.85;
        shake = 5;
        burst(player.x, player.y, "#d69373", 8);
        onEvent("hurt");
        const dx = e.x - player.x,
          dy = e.y - player.y,
          n = Math.hypot(dx, dy) || 1;
        move(e, (dx / n) * 38, (dy / n) * 38, e.radius);
        if (player.hp <= 0) {
          modeTo("dead");
          hud();
          onEvent("dead");
          return;
        }
      }
    }
    for (let i = bullets.length - 1; i >= 0; i--) {
      const b = bullets[i];
      b.life -= dt;
      b.x += b.vx * dt;
      b.y += b.vy * dt;
      let hit = false;
      if (
        blocks.some(
          (r) =>
            b.x >= r.x && b.x <= r.x + r.w && b.y >= r.y && b.y <= r.y + r.h,
        )
      ) {
        hit = true;
        burst(b.x, b.y, "#d4c6a0", 3);
      }
      if (!hit)
        for (let j = enemies.length - 1; j >= 0; j--) {
          const e = enemies[j];
          if (Math.hypot(e.x - b.x, e.y - b.y) < e.radius + 5) {
            e.hp--;
            e.hit = 0.1;
            hit = true;
            burst(b.x, b.y, "#b7c99a", reduced ? 2 : 7);
            if (e.hp <= 0) {
              kills++;
              score +=
                e.kind === "brute" ? 250 : e.kind === "runner" ? 150 : 100;
              stains.push({ x: e.x, y: e.y, a: e.angle });
              enemies.splice(j, 1);
              onEvent("kill");
            }
            break;
          }
        }
      if (hit || b.life <= 0 || b.x < 0 || b.x > W || b.y < 0 || b.y > H)
        bullets.splice(i, 1);
    }
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.life -= dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      if (p.life <= 0) particles.splice(i, 1);
    }
    if (!spawn.length && !enemies.length) {
      if (wave + 1 < level.waves.length) {
        modeTo("upgrade");
        hud();
      } else {
        modeTo("cleared");
        onComplete({ level: level.id, score, kills });
        onEvent("clear");
        hud();
      }
    }
    hudTick += dt;
    if (hudTick > 0.08) {
      hudTick = 0;
      hud();
    }
  }
  function actor(p, zombie = false) {
    const t = worldTime * 8 + (p.seed || 0),
      moving = zombie || Math.abs(input.x) + Math.abs(input.y) > 0.05;
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.fillStyle = "#00000055";
    ctx.beginPath();
    ctx.ellipse(3, 9, zombie ? p.radius + 3 : 17, 9, 0, 0, TAU);
    ctx.fill();
    ctx.rotate(p.angle + Math.PI / 2);
    if (!zombie && !reduced && p.inv > 0 && Math.floor(p.inv * 15) % 2 === 0)
      ctx.globalAlpha = 0.6;
    const size = p.kind === "brute" ? 1.35 : p.kind === "runner" ? 0.85 : 1;
    ctx.scale(size, size);
    ctx.fillStyle = zombie ? "#222b25" : "#142325";
    const walk = moving ? Math.sin(t) * 4 : 0;
    rectangle(ctx, -9, 8 + walk, 7, 12, 3);
    rectangle(ctx, 2, 8 - walk, 7, 12, 3);
    ctx.fillStyle = zombie
      ? p.hit > 0
        ? "#e2ecbd"
        : p.kind === "runner"
          ? "#6c4540"
          : GAME_DESIGN.colors.enemy
      : GAME_DESIGN.colors.player;
    rectangle(ctx, -12, -11, 24, 28, 7);
    ctx.fillStyle = zombie ? "#81926a" : "#a7b4a1";
    rectangle(ctx, -17, zombie ? -18 : -8, 7, zombie ? 29 : 21, 3);
    rectangle(ctx, 10, zombie ? -18 : -18, 7, zombie ? 29 : 25, 3);
    ctx.fillStyle = zombie ? "#a5b584" : "#d2cfb3";
    ctx.beginPath();
    ctx.ellipse(0, -13, 9, 10, 0, 0, TAU);
    ctx.fill();
    if (zombie) {
      ctx.fillStyle = p.kind === "runner" ? "#e39172" : "#c2cda0";
      ctx.fillRect(-6, -18, 4, 2);
      ctx.fillRect(3, -18, 4, 2);
      ctx.fillStyle = "#473a32";
      ctx.fillRect(-8, 3, 6, 8);
      ctx.fillRect(3, -5, 4, 12);
    } else {
      ctx.fillStyle = "#526458";
      ctx.beginPath();
      ctx.arc(0, -15, 10, Math.PI, TAU);
      ctx.fill();
      ctx.fillStyle = "#212d2b";
      ctx.fillRect(-8, -13, 16, 4);
      ctx.fillStyle = "#cfb471";
      ctx.fillRect(-4, 0, 8, 3);
      ctx.fillStyle = "#202b2e";
      rectangle(ctx, 9, -38, 6, 31, 2);
      ctx.fillStyle = "#7f8e86";
      ctx.fillRect(9, -27, 6, 4);
      if (flash > 0 && !reduced) {
        ctx.fillStyle = "#ffe1a3";
        ctx.beginPath();
        ctx.moveTo(6, -39);
        ctx.lineTo(12, -56);
        ctx.lineTo(19, -38);
        ctx.closePath();
        ctx.fill();
      }
    }
    ctx.restore();
    if (zombie && p.kind === "brute") {
      ctx.fillStyle = "#2e2523";
      ctx.fillRect(p.x - 18, p.y - 32, 36, 3);
      ctx.fillStyle = "#bd8a64";
      ctx.fillRect(p.x - 18, p.y - 32, (36 * p.hp) / p.maxHp, 3);
    }
  }
  function render() {
    const rect = canvas.getBoundingClientRect(),
      ratio = Math.min(window.devicePixelRatio || 1, 1.5),
      cw = Math.max(1, Math.round(rect.width * ratio)),
      ch = Math.max(1, Math.round(rect.height * ratio));
    if (canvas.width !== cw || canvas.height !== ch) {
      canvas.width = cw;
      canvas.height = ch;
    }
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);
    const zoom =
        Math.max(rect.width / W, rect.height / H) *
        (rect.width < 680 ? 1.12 : 1),
      vw = rect.width / zoom,
      vh = rect.height / zoom;
    view = {
      x: clamp(player.x - vw / 2, 0, Math.max(0, W - vw)),
      y: clamp(player.y - vh / 2, 0, Math.max(0, H - vh)),
      z: zoom,
    };
    ctx.save();
    ctx.scale(zoom, zoom);
    ctx.translate(
      -view.x + (reduced ? 0 : Math.sin(worldTime * 111) * shake),
      -view.y + (reduced ? 0 : Math.cos(worldTime * 93) * shake),
    );
    ctx.drawImage(background, 0, 0);
    ctx.fillStyle = "#743d353d";
    for (const s of stains) {
      ctx.save();
      ctx.translate(s.x, s.y);
      ctx.rotate(s.a);
      ctx.beginPath();
      ctx.ellipse(0, 0, 23, 12, 0, 0, TAU);
      ctx.fill();
      ctx.restore();
    }
    for (const e of spawn)
      if (e.delay < 0) {
        ctx.strokeStyle = "#d59a6b90";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(e.x, e.y, 24 + Math.sin(worldTime * 9) * 4, 0, TAU);
        ctx.stroke();
        ctx.fillStyle = "#e3af7720";
        ctx.beginPath();
        ctx.arc(e.x, e.y, 26, 0, TAU);
        ctx.fill();
      }
    const sorted = [
      ...enemies.map((e) => ({ p: e, z: true })),
      { p: player, z: false },
    ].sort((a, b) => a.p.y - b.p.y);
    for (const a of sorted) actor(a.p, a.z);
    if (pulseFlash > 0) {
      ctx.save();
      ctx.globalAlpha = reduced ? 0.18 : pulseFlash * 0.65;
      ctx.strokeStyle = "#c5efd2";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(
        player.x,
        player.y,
        loadout.pulseRadius * (reduced ? 1 : 1 - pulseFlash / 0.6),
        0,
        TAU,
      );
      ctx.stroke();
      ctx.restore();
    }
    for (const b of bullets) {
      ctx.strokeStyle = "#ffdf9c";
      ctx.lineWidth = 2.8;
      ctx.beginPath();
      ctx.moveTo(b.x, b.y);
      ctx.lineTo(b.x - b.vx * 0.018, b.y - b.vy * 0.018);
      ctx.stroke();
    }
    for (const p of particles) {
      ctx.globalAlpha = p.life / p.max;
      ctx.fillStyle = p.color;
      ctx.fillRect(p.x, p.y, 3, 3);
    }
    ctx.globalAlpha = 1;
    if (mode === "menu") {
      ctx.save();
      ctx.globalAlpha = 0.75;
      actor(
        { x: 930, y: 330, angle: -2.2, seed: 3, radius: 14, kind: "walker" },
        true,
      );
      actor(
        { x: 760, y: 570, angle: -2.7, seed: 6, radius: 14, kind: "walker" },
        true,
      );
      ctx.restore();
    }
    ctx.restore();
    const vignette = ctx.createRadialGradient(
      rect.width * 0.5,
      rect.height * 0.46,
      rect.width * 0.1,
      rect.width * 0.5,
      rect.height * 0.46,
      Math.max(rect.width, rect.height) * 0.68,
    );
    vignette.addColorStop(0, "#030a0a00");
    vignette.addColorStop(1, "#030a0aaf");
    ctx.fillStyle = vignette;
    ctx.fillRect(0, 0, rect.width, rect.height);
    if (!reduced) {
      ctx.fillStyle = "#d5d8b515";
      for (let i = 0; i < 30; i++) {
        const x = (i * 151 + worldTime * 5) % rect.width,
          y = (i * 89 + Math.sin(worldTime * 0.2 + i) * 20) % rect.height;
        ctx.fillRect(x, y, 1.5, 1.5);
      }
    }
    if (mode === "playing") {
      for (const enemy of enemies) {
        const sx = (enemy.x - view.x) * zoom,
          sy = (enemy.y - view.y) * zoom;
        if (
          sx > 10 &&
          sx < rect.width - 10 &&
          sy > 90 &&
          sy < rect.height - 145
        )
          continue;
        const angle = Math.atan2(sy - rect.height / 2, sx - rect.width / 2),
          x = clamp(sx, 14, rect.width - 14),
          y = clamp(sy, 100, rect.height - 150);
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(angle);
        ctx.fillStyle = "#d8a675b0";
        ctx.beginPath();
        ctx.moveTo(6, 0);
        ctx.lineTo(-4, -4);
        ctx.lineTo(-4, 4);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      }
    }
    if (input.aim && mode === "playing") {
      const x = (input.aim.x - view.x) * zoom,
        y = (input.aim.y - view.y) * zoom;
      ctx.strokeStyle = "#d5e3cb90";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(x, y, 10, 0, TAU);
      ctx.moveTo(x - 15, y);
      ctx.lineTo(x - 6, y);
      ctx.moveTo(x + 6, y);
      ctx.lineTo(x + 15, y);
      ctx.moveTo(x, y - 15);
      ctx.lineTo(x, y - 6);
      ctx.moveTo(x, y + 6);
      ctx.lineTo(x, y + 15);
      ctx.stroke();
    }
  }
  function point(event) {
    const r = canvas.getBoundingClientRect();
    return {
      x: clamp((event.clientX - r.left) / view.z + view.x, 0, W),
      y: clamp((event.clientY - r.top) / view.z + view.y, 0, H),
    };
  }
  function loop(t) {
    if (destroyed) return;
    const dt = Math.min((t - (last || t)) / 1000, 0.04);
    last = t;
    if (mode === "playing") step(dt);
    else if (mode === "menu" && !reduced) worldTime += dt;
    render();
    frame = requestAnimationFrame(loop);
  }
  reset(0);
  frame = requestAnimationFrame(loop);
  return {
    start,
    pause,
    resume,
    menu,
    restart,
    next,
    setInput,
    dash,
    pulse,
    chooseUpgrade,
    point,
    setReduced: (value) => {
      reduced = !!value;
    },
    destroy: () => {
      destroyed = true;
      cancelAnimationFrame(frame);
    },
  };
}
