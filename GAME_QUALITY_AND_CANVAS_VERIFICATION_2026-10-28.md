# Game quality, canvas evidence and safe retries ? 2026-10-28

The latest failed game verification repeatedly declared painted movement, shooting and wave completion unautomatable, then failed guessed Settings targets. A verification-incomplete retry could resend the compiled game through implementation rather than retaining it.

The verifier now supports read-only rememberFrame/frameChanged/frameStable actions on a named canvas. It samples 64x64 pixels of a validated region without reading or changing game state. Stability tolerance is capped, captures and comparisons must identify the same target/region, and source remains preserved when pixels are unavailable. These are scoped rendered-change checks, not exhaustive game or aesthetic certification.

Bounded hold input can stop at a named visible outcome; keys are released in all cases and further holds skip already-visible outcomes. Canvas workflows with actual frame capture/comparison may use 30 seconds of bounded input, 60 seconds per plan; other workflows retain 15/45-second limits. Parent execution deadlines remain authoritative.

Compiled verification-incomplete requests with no confirmed application failures resume verification/rebuild of saved source. Confirmed failures and interrupted implementation retain the implementation-repair path. No verification failure is converted into a passing build.

Game engineering and quality guidance now requires genre-appropriate scene/character finish, real skill effects/cooldowns when requested, readable HUD and in-play evidence. Abstract/puzzle user preferences remain authoritative.

Validation: 211 isolated release regression tests passed before final schema/tolerance tightening; 53 targeted final canvas/input/schema/retry checks and 38 game-quality/design/trend checks passed. A configured-model synthetic test generated and executed rememberFrame/hold/frameChanged plus firing/score checks successfully. No private game source was sent to a model.

The actual game was separately rebuilt as an original 2D survival roguelite with five sectors, two waves per sector, original canvas/vector art, Dash/Pulse, between-wave upgrade choices, responsive keyboard/mouse/touch controls and retained saved-state keys. All eight reviewed browser requirements passed at 1440px and 390px using normal input and the verifier's new frame actions. Engine tests cover all five sectors, real skill damage/cooldowns, upgrade effects/carry, fair loss/retry and a single simulation owner. Official public Brotato/Megabonk pages and screenshots informed genre-readability/build choices; their art is not shipped. Current references are not a claim of global trend rank.
