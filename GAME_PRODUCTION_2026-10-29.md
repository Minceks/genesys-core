# Autonomous game production

The prior recovery rebuilt one customer game manually. That did not make future agent builds equivalent. This change puts reusable game engineering, original scene art, responsive UI and executable quality checks into the agent's normal production path.

## What changes

- Fresh games enter game production by default, independently of the generic parallel-build flag and Gemini configuration. Other product types retain their existing path.
- Compatible top-down zombie/wave-survival requests use the `survival-v1` foundation. The agent authors a strict design configuration: original identity, copy, scene and actor palette, mission content, later-sector encounters and skill cooldowns. The tested teaching encounter, renderer, single simulation loop, collision recovery, controls, upgrades and complete run states are reusable infrastructure. No developer rewrites each generated game.
- The foundation has a real contract and server-owned regression suite. The agent executes ordinary keyboard/pointer inputs, canvas comparisons and HUD assertions, normal combat through upgrades/sector completion, save/reload/reset, reduced motion, native simultaneous CDP touch input, rotation/reload, natural contact loss and retry. No game-state hooks or fabricated verification cache are installed. Extra or changed contract requirements invalidate the specialized test route.
- Unsupported genres and explicit incompatible features retain bespoke generation. They must not silently become the survival preset. That path plans the scene and interface, authors engine and art together, then authors UI and CSS against the actual engine source. Partial work and its plan survive failures.
- Screenshot review retains real rendered action frames, including when later checks finish on menus. Matching action games receive the accepted original game frame as a finish reference. A menu alone, a decorative canvas or passing compilation does not establish finish. Major findings and unavailable game-design approval block delivery while preserving the build.
- Agent browsers use the configured preview domain. A recognized external network warning is a preview-access failure and cannot trigger game-source repair.
- Games receive an isolated entry point instead of generic website styles. The survival foundation includes swipeable phone sector cards, touch guidance and landscape controls bounded to the viewport.
- Visual repairs use a focused, source-aware model call with bounded CSS overrides or configuration replacements. Encounter mechanics, skill balance and saved-data keys are protected during visual polish. Entry and gameplay screenshots are judged against their corresponding accepted references.
- Completed model calls settle reservations against reported usage. Unknown usage and historical reservations remain charged; the existing daily limit still applies. This prevents unused output allowances from exhausting the budget during review and repair.

## Scope

This is a tested foundation and a stronger production/review workflow, not model training or a guarantee about every future game. The reusable foundation currently serves the compatible top-down survival case; explicit FPS/3D, multiplayer, puzzles, different sector counts, custom numeric wave counts and other incompatible mechanics do not inherit it. The original reference screenshot is evaluation material and is never shipped as artwork in generated games.

## Evidence

Local runtime audits exercise all five sectors, real skill damage/cooldowns, upgrades, progression, loss/retry, the single RAF lifecycle and contact-damage recovery. The full foundation browser regression passes ten requirements without model calls or state injection. Fresh real-agent evaluation receipts are retained locally under `.test-game-production-*`; they distinguish unsuccessful attempts from completed approvals and record that generated game source was not edited manually.
