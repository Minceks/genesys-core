import { GAME_DESIGN } from "./gameDesign.js";
﻿import React, { useEffect, useRef, useState } from "react";
import { createGame, LEVELS } from "./projectLogic";
import { usePersistentState } from "./usePersistentState";
import "./styles.css";
function Icon({ type = "cross", size = 20 }) {
  const paths = {
    pause: "M8 5v14M16 5v14",
    play: "m9 5 10 7-10 7Z",
    gear: "m12 3 2 3 4-.2.2 4 2 2-2 2-.2 4-4-.2-2 3-2-3-4 .2-.2-4-2-2 2-2 .2-4 4 .2Z",
    cross: "M12 3v4m0 10v4M3 12h4m10 0h4M7 7l10 10M7 17 17 7",
    arrow: "M4 12h15m-6-6 6 6-6 6",
    lock: "M6 11h12v10H6Zm3 0V7a3 3 0 0 1 6 0v4",
    sound: "m4 9 5-1 5-4v16l-5-4-5-1Zm13-2a7 7 0 0 1 0 10",
    close: "m6 6 12 12M6 18 18 6",
    shield: "m12 3 8 3v7c0 5-8 9-8 9s-8-4-8-9V6Z",
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[type] || paths.cross} />
    </svg>
  );
}
function Modal({ title, children, onClose, eyebrow }) {
  const box = useRef(null);
  useEffect(() => {
    const before = document.activeElement;
    box.current?.querySelector("button,input")?.focus();
    return () => {
      if (before?.isConnected) before.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onKeyDown={(e) => {
        if (e.repeat && (e.key === " " || e.key === "Enter")) {
          e.preventDefault();
          return;
        }
        if (e.key === "Escape" && onClose) {
          e.preventDefault();
          onClose();
        }
        if (e.key === "Tab") {
          const els = [
            ...box.current.querySelectorAll(
              "button:not([disabled]),input,a[href]",
            ),
          ];
          if (!els.length) return;
          const first = els[0],
            last = els.at(-1);
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }}
    >
      <section
        className="field-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        ref={box}
      >
        <span className="eyebrow">{eyebrow || GAME_DESIGN.operation}</span>
        <h2 id="dialog-title">{title}</h2>
        {children}
      </section>
    </div>
  );
}
export default function App() {
  const canvas = useRef(null),
    engine = useRef(null),
    keys = useRef(new Set()),
    audio = useRef(null),
    soundOn = useRef(false),
    prefs = useRef(null),
    joyId = useRef(null),
    pointerFire = useRef(false),
    menuButton = useRef(null);
  const [settings, setSettings] = usePersistentState(GAME_DESIGN.storageKey + ":settings", {
    persistProgress: true,
    sound: false,
    reducedMotion: false,
  });
  const [progress, setProgress] = usePersistentState(GAME_DESIGN.storageKey + ":progress", {
    level: 1,
    wave: 1,
    maxWave: 1,
    unlocked: 1,
    bestScore: (() => { try { return Math.max(0, Number(JSON.parse(localStorage.getItem(GAME_DESIGN.storageKey + ":best") || "0")) || 0); } catch { return 0; } })(),
  });
  const [sessionUnlocked, setSessionUnlocked] = useState(1);
  const [entryWave, setEntryWave] = useState(1);
  const progressRef = useRef(progress), savedTerminal = useRef(null);
  progressRef.current = progress;
  const [mode, setMode] = useState("menu"),
    [selected, setSelected] = useState(() =>
      settings.persistProgress
        ? Math.min(4, Math.max(0, (progress.level || 1) - 1))
        : 0,
    ),
    [hud, setHUD] = useState({
      level: 1,
      wave: 1,
      waves: 2,
      score: 0,
      kills: 0,
      health: 5,
      enemies: 0,
    }),
    [settingsOpen, setSettingsOpen] = useState(false),
    [systemMotion, setSystemMotion] = useState(false),
    [thumb, setThumb] = useState({ x: 0, y: 0 }),
    [result, setResult] = useState(null);
  prefs.current = settings;
  soundOn.current = !!settings.sound;
  const reduce = systemMotion || !!settings.reducedMotion,
    unlocked = Math.min(
      5,
      Math.max(1, sessionUnlocked, progress.unlocked || progress.level || 1),
    );
  function tone(type) {
    if (!soundOn.current) return;
    try {
      const ac =
        audio.current ||
        (audio.current = new (
          window.AudioContext || window.webkitAudioContext
        )());
      if (ac.state === "suspended") ac.resume();
      const o = ac.createOscillator(),
        g = ac.createGain();
      o.type = type === "shot" ? "triangle" : "sine";
      o.frequency.setValueAtTime(
        type === "shot"
          ? 130
          : type === "kill"
            ? 420
            : type === "hurt"
              ? 70
              : 600,
        ac.currentTime,
      );
      o.frequency.exponentialRampToValueAtTime(
        type === "shot" ? 45 : 160,
        ac.currentTime + 0.08,
      );
      g.gain.setValueAtTime(type === "shot" ? 0.025 : 0.04, ac.currentTime);
      g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.11);
      o.connect(g);
      g.connect(ac.destination);
      o.start();
      o.stop(ac.currentTime + 0.12);
    } catch {}
  }
  useEffect(() => {
    document.title = "Wave Zombie — Nightfall";
    const game = createGame(canvas.current, {
      onHUD: (value) => {
        setHUD(value);
        const absoluteWave = (value.level - 1) * 2 + value.wave;
        if (prefs.current.persistProgress && absoluteWave > (progressRef.current.maxWave || 1))
          setProgress(old => ({...old, maxWave:absoluteWave,unlockedWave:Math.max(old.unlockedWave || 1,absoluteWave)}));
        if (((value.mode === "dead" && value.health <= 0) || (["cleared","victory"].includes(value.mode) && value.enemies === 0)) && savedTerminal.current !== value.mode) {
          savedTerminal.current = value.mode;
          if (prefs.current.persistProgress) setProgress(old => {
            const bestScore = Math.max(old.bestScore || 0, value.score);
            try { localStorage.setItem(GAME_DESIGN.storageKey + ":best",JSON.stringify(bestScore)); } catch {}
            return {...old, bestScore, maxWave:Math.max(old.maxWave || 1,absoluteWave),
              lastRun:{score:value.score, wave:absoluteWave, outcome:value.mode === "dead" ? "Defeat" : "Sector secured"}};
          });
        } else if(value.mode === "playing") savedTerminal.current = null;
      },
      onMode: setMode,
      onEvent: tone,
      onComplete: (value) => {
        setResult(value);
        setSessionUnlocked((old) =>
          Math.min(5, Math.max(old, value.level + 1)),
        );
        if (prefs.current.persistProgress)
          setProgress((old) => ({
            ...old,
            level: Math.min(5, value.level + 1),
            wave: 1,
            maxWave: Math.max(old.maxWave || 1, value.level * 2),
            unlockedWave: Math.min(10, Math.max(old.unlockedWave || 1, value.level * 2 + 1)),
            unlocked: Math.min(
              5,
              Math.max(old.unlocked || old.level || 1, value.level + 1),
            ),
            bestScore: Math.max(old.bestScore || 0, value.score),
          }));
      },
    });
    engine.current = game;
    const route = () => {
      const match = location.hash.match(/^#\/play(?:\/wave\/(\d+))?$/);
      if (!match) { game.menu(); setResult(null); return; }
      const requested = Math.max(1, Math.min(10, Number(match[1]) || 1));
      const allowed = Math.min(requested, progressRef.current.unlockedWave || progressRef.current.maxWave || 1);
      game.start(Math.floor((allowed-1)/2),false,(allowed-1)%2);
    };
    route();
    window.addEventListener("popstate",route);
    window.addEventListener("hashchange",route);
    return () => {
      window.removeEventListener("popstate",route);
      window.removeEventListener("hashchange",route);
      game.destroy();
      engine.current = null;
      audio.current?.close();
    };
  }, []);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)"),
      change = () => setSystemMotion(mq.matches);
    change();
    mq.addEventListener("change", change);
    return () => mq.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    engine.current?.setReduced(reduce);
  }, [reduce]);
  useEffect(() => {
    if (mode === "playing" && !settingsOpen) canvas.current?.focus();
    else {
      if (mode === "menu" && !settingsOpen) menuButton.current?.focus();
      keys.current.clear();
      pointerFire.current = false;
      joyId.current = null;
      setThumb({ x: 0, y: 0 });
    }
  }, [mode, settingsOpen]);
  function movement() {
    const k = keys.current;
    engine.current?.setInput({
      x:
        Number(k.has("d") || k.has("arrowright")) -
        Number(k.has("a") || k.has("arrowleft")),
      y:
        Number(k.has("s") || k.has("arrowdown")) -
        Number(k.has("w") || k.has("arrowup")),
      fire: k.has(" ") || pointerFire.current,
    });
  }
  useEffect(() => {
    const down = (e) => {
      if (e.target.closest("input,select,textarea") || settingsOpen) return;
      const key = e.key.toLowerCase();
      if (mode === "playing" && (key === "shift" || key === "e")) {
        e.preventDefault();
        engine.current.dash();
        return;
      }
      if (mode === "playing" && key === "q") {
        e.preventDefault();
        engine.current.pulse();
        return;
      }
      if (key === " " && e.target.closest("button")) return;
      if (key === "escape") {
        if (mode === "playing") engine.current.pause();
        else if (mode === "paused") engine.current.resume();
        return;
      }
      if (
        mode !== "playing" ||
        ![
          "w",
          "a",
          "s",
          "d",
          "arrowup",
          "arrowdown",
          "arrowleft",
          "arrowright",
          " ",
        ].includes(key)
      )
        return;
      e.preventDefault();
      keys.current.add(key);
      if (!pointerFire.current) engine.current.setInput({ aim: null });
      movement();
    };
    const up = (e) => {
      keys.current.delete(e.key.toLowerCase());
      if (mode === "playing") movement();
    };
    const blur = () => {
      keys.current.clear();
      engine.current?.setInput({ x: 0, y: 0, fire: false, aim: null });
      if (mode === "playing") engine.current.pause();
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    window.addEventListener("blur", blur);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
      window.removeEventListener("blur", blur);
    };
  }, [mode, settingsOpen]);
  function deploy(index = selected, waveIndex = 0, direct = false) {
    setResult(null);
    keys.current.clear();
    history.pushState(null,"",direct ? `#/play/wave/${index*2+waveIndex+1}` : "#/play");
    engine.current.start(index,false,waveIndex);
    canvas.current.focus();
  }
  function returnMenu() {
    keys.current.clear();
    setResult(null);
    history.pushState(null,"","#/");
    engine.current.menu();
    setSelected(Math.min(selected, unlocked - 1));
  }
  function toggleSettings() {
    if (mode === "playing") engine.current.pause();
    setSettingsOpen(true);
  }
  function releaseFire() {
    pointerFire.current = false;
    engine.current?.setInput({
      fire: keys.current.has(" "),
      ...(keys.current.has(" ") ? { aim: null } : {}),
    });
  }
  function joystick(e) {
    const r = e.currentTarget.getBoundingClientRect(),
      dx = Math.max(
        -1,
        Math.min(1, (e.clientX - r.left - r.width / 2) / (r.width * 0.38)),
      ),
      dy = Math.max(
        -1,
        Math.min(1, (e.clientY - r.top - r.height / 2) / (r.height * 0.38)),
      );
    setThumb({ x: dx * 22, y: dy * 22 });
    engine.current?.setInput({
      x: Math.abs(dx) < 0.15 ? 0 : dx,
      y: Math.abs(dy) < 0.15 ? 0 : dy,
      aim: null,
    });
  }
  function releaseJoystick() {
    joyId.current = null;
    setThumb({ x: 0, y: 0 });
    engine.current?.setInput({ x: 0, y: 0 });
  }
  const active = LEVELS[hud.level - 1] || LEVELS[0],
    modal =
      settingsOpen ||
      ["paused", "upgrade", "cleared", "dead", "victory"].includes(mode);
  return (
    <div className={"nightfall" + (reduce ? " reduced-motion" : "")}>
      <header className="command-bar">
        <button
          className="brand"
          onClick={() => {
            if (mode === "playing") engine.current.pause();
            else returnMenu();
          }}
          aria-label={GAME_DESIGN.title}
        >
          <span className="brand-mark">
            <Icon type="shield" />
          </span>
          <span>
            {GAME_DESIGN.brand[0]}<span className="brand-light">{GAME_DESIGN.brand[1]}</span>
            <small>{GAME_DESIGN.subtitle}</small>
          </span>
        </button>
        <div className="signal">
          <i /> LOCAL SIGNAL ACTIVE <span>●</span> NO NETWORK REQUIRED
        </div>
        <div className="header-actions">
          <button
            className={"icon-button " + (settings.sound ? "enabled" : "")}
            aria-label={settings.sound ? "Mute sound" : "Enable sound"}
            onClick={() => {
              setSettings((old) => ({ ...old, sound: !old.sound }));
              if (!settings.sound) {
                soundOn.current = true;
                tone("start");
              }
            }}
          >
            <Icon type="sound" />
          </button>
          <button
            className="icon-button"
            aria-label="Open settings"
            onClick={toggleSettings}
          >
            <Icon type="gear" />
          </button>
        </div>
      </header>
      <main className="game-stage">
        <div className="stage-body" inert={modal ? true : undefined}>
          <canvas
            ref={canvas}
            aria-label="Playfield canvas"
            tabIndex={0}
            onPointerMove={(e) => {
              if (mode === "playing" && e.pointerType !== "touch")
                engine.current.setInput({ aim: engine.current.point(e) });
            }}
            onPointerDown={(e) => {
              if (mode === "playing" && e.button === 0) {
                e.currentTarget.setPointerCapture(e.pointerId);
                pointerFire.current = true;
                engine.current.setInput({
                  aim: engine.current.point(e),
                  fire: true,
                });
              }
            }}
            onPointerUp={releaseFire}
            onPointerCancel={releaseFire}
          />
          <div className="screen-grain" />
          {mode === "menu" && (
            <div className="deployment-screen">
              <div className="deployment-copy">
                <span className="eyebrow">
                  <i /> {GAME_DESIGN.eyebrow}
                </span>
                <h1>
                  {GAME_DESIGN.headline[0]}
                  <br />
                  {GAME_DESIGN.headline[1]}
                  <br />
                  <em>{GAME_DESIGN.headline[2]}</em>
                </h1>
                <p>
                  {GAME_DESIGN.description}
                </p>
                <button
                  ref={menuButton}
                  className="deploy-button"
                  aria-label="Start game"
                  onClick={() => deploy()}
                >
                  <span>
                    DEPLOY TO SECTOR {String(selected + 1).padStart(2, "0")}
                  </span>
                  <Icon type="arrow" size={23} />
                </button>
                <div className="mission-brief">
                  <span>MISSION BRIEF</span>
                  <strong>{LEVELS[selected].name}</strong>
                  <p>{LEVELS[selected].brief}</p>
                </div>
              </div>
              <div className="world-label">
                <span>ZONE 0{selected + 1}</span>
                <strong>{LEVELS[selected].tag}</strong>
                <div>
                  <i /> {GAME_DESIGN.enemySignal}
                </div>
              </div>
              <div className="sector-selection">
                <div className="sector-heading">
                  <span>{GAME_DESIGN.operation}</span>
                  <small>{unlocked} / 5 SECTORS AVAILABLE</small>
                </div>
                <div className="sector-list">
                  {LEVELS.map((level, index) => (
                    <button
                      key={level.id}
                      disabled={level.id > unlocked}
                      className={
                        "sector " + (index === selected ? "selected" : "")
                      }
                      aria-label={"Select level " + level.id}
                      aria-pressed={index === selected}
                      onClick={() => setSelected(index)}
                    >
                      <span className="sector-index">
                        {String(level.id).padStart(2, "0")}
                      </span>
                      <span className="sector-name">
                        {level.name}
                        <small>
                          {level.id > unlocked
                            ? "LOCKED"
                            : index === selected
                              ? "READY TO DEPLOY"
                              : "AVAILABLE"}
                        </small>
                      </span>
                      {level.id > unlocked ? (
                        <Icon type="lock" size={15} />
                      ) : (
                        <span className="sector-dot" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
          {mode !== "menu" && (
            <>
              <div className="mission-hud">
                <div className="zone-status">
                  <span className="eyebrow">
                    SECTOR{" "}
                    <output aria-label="Level number">{hud.level}</output> / 05
                  </span>
                  <strong>{active.name}</strong>
                  <div className="run-build">
                    <span>
                      FIRE{" "}
                      <output aria-label="Fire rate multiplier">
                        {(1 / (hud.fireMultiplier || 1)).toFixed(2)}
                      </output>
                      ?
                    </span>
                    <span>
                      PULSE{" "}
                      <output aria-label="Pulse power">
                        {hud.pulsePower || 2}
                      </output>
                    </span>
                  </div>
                </div>
                <div className="wave-status">
                  <span>WAVE</span>
                  <strong>
                    <output aria-label="Wave number">{hud.wave}</output>
                    <small> / 0{hud.waves}</small>
                  </strong>
                  <div className="wave-bars">
                    {Array.from({ length: hud.waves }, (_, i) => (
                      <i key={i} className={i < hud.wave ? "lit" : ""} />
                    ))}
                  </div>
                </div>
                <div className="score-status">
                  <span>SCORE</span>
                  <output aria-label="Score">
                    {String(hud.score).padStart(5, "0")}
                  </output>
                </div>
                <button
                  className="pause-button"
                  aria-label="Pause game"
                  onClick={() => engine.current.pause()}
                >
                  <Icon type="pause" />
                </button>
              </div>
              {hud.intermission && (
                <div className="wave-notice" role="status">
                  <span>WAVE {hud.wave} CLEAR</span>
                  <strong>Reinforcements inbound</strong>
                </div>
              )}
              <div className="health-hud">
                <div>
                  <span>VITALS</span>
                  <strong>
                    <output aria-label="Health">{hud.health}</output> /{" "}
                    {hud.maxHealth || 5}
                  </strong>
                </div>
                <div className="health-cells">
                  {Array.from({ length: hud.maxHealth || 5 }, (_, i) => (
                    <i key={i} className={i < hud.health ? "alive" : ""} />
                  ))}
                </div>
                <span className="remaining">
                  <b />
                  <output aria-label="Infected remaining">
                    {hud.enemies}
                  </output>{" "}
                  INFECTED REMAINING
                </span>
              </div>
              <div className="skill-tray" aria-label="Active skills">
                <button
                  className="skill-button"
                  aria-label="Dash skill"
                  title="Dash (Shift or E)"
                  disabled={hud.dashCooldown > 0}
                  onClick={() => engine.current.dash()}
                >
                  <kbd>E</kbd>
                  <Icon type="arrow" />
                  <span>DASH</span>
                  <small>
                    {hud.dashCooldown > 0 ? (
                      <>
                        <output aria-label="Dash cooldown">
                          {Math.ceil(hud.dashCooldown)}
                        </output>
                        s
                      </>
                    ) : (
                      "READY"
                    )}
                  </small>
                </button>
                <button
                  className="skill-button pulse-skill"
                  aria-label="Pulse skill"
                  title="Shock pulse (Q)"
                  disabled={hud.pulseCooldown > 0}
                  onClick={() => engine.current.pulse()}
                >
                  <kbd>Q</kbd>
                  <Icon type="cross" />
                  <span>PULSE</span>
                  <small>
                    {hud.pulseCooldown > 0 ? (
                      <>
                        <output aria-label="Pulse cooldown">
                          {Math.ceil(hud.pulseCooldown)}
                        </output>
                        s
                      </>
                    ) : (
                      "READY"
                    )}
                  </small>
                </button>
              </div>
              <div className="field-controls">
                <div
                  role="group"
                  aria-label="Movement joystick"
                  tabIndex={0}
                  className="movement-pad"
                  onPointerDown={(e) => {
                    e.preventDefault();
                    joyId.current = e.pointerId;
                    e.currentTarget.setPointerCapture(e.pointerId);
                    joystick(e);
                  }}
                  onPointerMove={(e) => {
                    if (joyId.current === e.pointerId) joystick(e);
                  }}
                  onPointerUp={releaseJoystick}
                  onPointerCancel={releaseJoystick}
                  onLostPointerCapture={releaseJoystick}
                >
                  <span className="pad-cross">+</span>
                  <span
                    className="pad-thumb"
                    style={{
                      transform: `translate(${thumb.x}px,${thumb.y}px)`,
                    }}
                  />
                  <small>MOVE</small>
                </div>
                <button
                  className="fire-control"
                  aria-label="Fire weapon"
                  onPointerDown={(e) => {
                    e.preventDefault();
                    e.currentTarget.setPointerCapture(e.pointerId);
                    pointerFire.current = true;
                    engine.current.setInput({ fire: true, aim: null });
                  }}
                  onKeyDown={(e) => {
                    if (e.key === " " || e.key === "Enter") {
                      e.preventDefault();
                      pointerFire.current = true;
                      engine.current.setInput({ fire: true, aim: null });
                    }
                  }}
                  onKeyUp={releaseFire}
                  onPointerUp={releaseFire}
                  onPointerCancel={releaseFire}
                  onLostPointerCapture={releaseFire}
                >
                  <Icon size={30} />
                  <span>FIRE</span>
                </button>
              </div>
            </>
          )}
        </div>
        {settingsOpen ? (
          <Modal
            title="Field settings"
            eyebrow="YOUR LOADOUT"
            onClose={() => setSettingsOpen(false)}
          >
            <p className="dialog-copy">
              Your progress stays on this device. No account, no server.
            </p>
            <label className="setting-row">
              <span>
                <strong>Persist Progress</strong>
                <small>
                  Keep cleared sectors and your best score. Turning off clears
                  saved progress.
                </small>
              </span>
              <input
                aria-label="Persist Progress"
                type="checkbox"
                checked={!!settings.persistProgress}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setSettings((old) => ({ ...old, persistProgress: checked }));
                  if (!checked) {
                    setProgress({
                      level: 1,
                      wave: 1,
                      maxWave: 1,
                      unlocked: 1,
                      bestScore: 0,
                    });
                    setSessionUnlocked(1);
                    setSelected(0);
                  }
                }}
              />
            </label>
            <label className="setting-row">
              <span>
                <strong>Reduced motion</strong>
                <small>
                  {systemMotion
                    ? "System preference is active."
                    : "Reduce flashes, camera shake and drifting dust."}
                </small>
              </span>
              <input
                aria-label="Reduced motion"
                type="checkbox"
                checked={!!settings.reducedMotion}
                onChange={(e) =>
                  setSettings((old) => ({
                    ...old,
                    reducedMotion: e.target.checked,
                  }))
                }
              />
            </label>
            <label className="setting-row">
              <span>
                <strong>Sound effects</strong>
                <small>Procedural weapon and combat audio.</small>
              </span>
              <input
                aria-label="Sound effects"
                type="checkbox"
                checked={!!settings.sound}
                onChange={(e) => {
                  soundOn.current = e.target.checked;
                  setSettings((old) => ({ ...old, sound: e.target.checked }));
                  if (e.target.checked) tone("start");
                }}
              />
            </label>
            <button
              className="dialog-primary"
              onClick={() => setSettingsOpen(false)}
            >
              Return to field
            </button>
            <button
              className="text-button"
              onClick={() => {
                setProgress({
                  level: 1,
                  wave: 1,
                  maxWave: 1,
                  unlocked: 1,
                  bestScore: 0,
                });
                setSessionUnlocked(1);
                setEntryWave(1);
                savedTerminal.current = null;
                try { localStorage.removeItem(GAME_DESIGN.storageKey + ":best"); } catch {}
                setSelected(0);
              }}
            >
              Clear saved progress
            </button>
          </Modal>
        ) : mode === "paused" ? (
          <Modal
            title="Paused"
            eyebrow="TAKE A BREATH"
            onClose={() => engine.current.resume()}
          >
            <p className="dialog-copy">
              The world can wait. Your run is right where you left it.
            </p>
            <button
              className="dialog-primary"
              onClick={() => engine.current.resume()}
            >
              Resume game <Icon type="play" size={16} />
            </button>
            <button
              className="dialog-secondary"
              onClick={() => {
                keys.current.clear();
                engine.current.restart();
              }}
            >
              Restart level
            </button>
            <button className="text-button" onClick={returnMenu}>
              Return to menu
            </button>
          </Modal>
        ) : mode === "upgrade" ? (
          <Modal title="Choose your edge" eyebrow="WAVE CLEAR / BUILD YOUR RUN">
            <p className="dialog-copy">
              One upgrade. A different way to survive the next wave. Your build
              carries into the next sector.
            </p>
            <div className="upgrade-options">
              <button
                className="upgrade-option"
                aria-label="Choose Rapid Fire"
                onClick={() => engine.current.chooseUpgrade("rapid")}
              >
                <span className="upgrade-icon"><Icon type="cross" size={24} /></span>
                <span>
                  <strong>Rapid fire</strong>
                  <small>25% faster shooting. Keep the pressure on.</small>
                </span>
                <b>FIRE RATE</b>
              </button>
              <button
                className="upgrade-option"
                aria-label="Choose Field Medic"
                disabled={
                  (hud.maxHealth || 5) >= 8 &&
                  hud.health >= (hud.maxHealth || 5)
                }
                onClick={() => engine.current.chooseUpgrade("medic")}
              >
                <span className="upgrade-icon">+</span>
                <span>
                  <strong>Field medic</strong>
                  <small>
                    {(hud.maxHealth || 5) >= 8
                      ? "Restore 2 health. Maximum health is capped at 8."
                      : "+1 maximum health. Restore 2 health now."}
                  </small>
                </span>
                <b>SURVIVAL</b>
              </button>
              <button
                className="upgrade-option"
                aria-label="Choose Charged Pulse"
                onClick={() => engine.current.chooseUpgrade("pulse")}
              >
                <span className="upgrade-icon"><Icon type="cross" size={24} /></span>
                <span>
                  <strong>Charged pulse</strong>
                  <small>
                    {(hud.pulseRadius || 160) >= 250
                      ? "+1 pulse damage. Blast radius is at maximum."
                      : "+1 pulse damage and a wider shock radius."}
                  </small>
                </span>
                <b>ABILITY</b>
              </button>
            </div>
          </Modal>
        ) : mode === "cleared" ? (
          <Modal title="Sector secured" eyebrow="SIGNAL RESTORED">
            <div className="clear-symbol">
              <Icon type="shield" size={38} />
            </div>
            <p className="dialog-copy">
              {active.name} is clear.{" "}
              {hud.level < 5
                ? "The next sector is waiting."
                : "You made it through the night."}
            </p>
            <div className="result-stats">
              <span>
                <small>RUN SCORE</small>
                <strong>{hud.score}</strong>
              </span>
              <span>
                <small>ELIMINATIONS</small>
                <strong>{hud.kills}</strong>
              </span>
              <span>
                <small>VITALS</small>
                <strong>
                  {hud.health}/{hud.maxHealth || 5}
                </strong>
              </span>
            </div>
            <button
              className="dialog-primary"
              onClick={() => {
                if (hud.level === 5) returnMenu();
                else {
                  setSelected(hud.level);
                  engine.current.next();
                  canvas.current.focus();
                }
              }}
            >
              {hud.level === 5 ? "Return to menu" : "Next level"}
              <Icon type="arrow" size={18} />
            </button>
            <button
              className="dialog-secondary"
              onClick={() => engine.current.restart()}
            >
              Replay level
            </button>
            <button className="text-button" onClick={returnMenu}>
              Return to menu
            </button>
          </Modal>
        ) : mode === "dead" ? (
          <Modal title="Signal lost" eyebrow="OPERATOR DOWN">
            <p className="dialog-copy">
              The perimeter fell. Regroup, keep moving, and try a different
              line.
            </p>
            <div className="result-stats">
              <span>
                <small>SCORE</small>
                <strong>{hud.score}</strong>
              </span>
              <span>
                <small>ELIMINATIONS</small>
                <strong>{hud.kills}</strong>
              </span>
            </div>
            <button
              className="dialog-primary"
              onClick={() => {
                keys.current.clear();
                engine.current.restart();
                canvas.current.focus();
              }}
            >
              Retry level
            </button>
            <button className="text-button" onClick={returnMenu}>
              Return to menu
            </button>
          </Modal>
        ) : null}
      </main>
      <footer className="field-footer">
        <span>
          <i /> HOLD THE LINE. KEEP YOUR SIGNAL.
        </span>
        <div className="desktop-control-hints">
          <kbd>W A S D</kbd> MOVE <b>·</b> <kbd>SPACE</kbd> FIRE / AUTO-AIM{" "}
          <b>·</b> <kbd>Q / E</kbd> SKILLS <b>?</b> <kbd>ESC</kbd> PAUSE
        </div>
        <div className="mobile-control-hints">LEFT THUMB: MOVE / RIGHT THUMB: FIRE</div>
        <span>
          BEST{" "}
          <strong>{String(progress.bestScore || 0).padStart(5, "0")}</strong>
        </span>
      </footer>
    </div>
  );
}
