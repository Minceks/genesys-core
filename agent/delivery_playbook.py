"""Reusable craft lessons; product identity and features still come from the request."""

DELIVERY_STANDARD = '''DELIVERY CRAFT STANDARD
Use the finish of a deliberately designed, playable product as the baseline, not a
first-draft scaffold. Quality means a coherent identity, working primary journey,
finished secondary states and proof from the rendered result. Do not reuse the same
dark theme, survival genre, layout or feature list for unrelated requests.
Before coding, choose actual type sizes, spacing, colors, art treatment and phone
composition; map each requested action to its state transition and visible result.
Study relevant rendered examples when available, then implement original adaptations
of their hierarchy, readability and interaction patterns. Never treat a title as
visual research or a popularity claim as evidence. Disclose unavailable research.
Build the complete journey before polish: entry, meaningful action, outcome, return,
reload and recovery where applicable. Keep one owner for authoritative state. Reset
dependent selections when their parent changes; handle local calendar dates locally.
Show inline validation after attempted submission, stable accessible names and clear
selected/disabled/loading/success states. Fixed navigation must reserve space for
content and cannot cover actions on a phone. Preserve existing data keys on repairs.
For games, review play as well as menus: original genre-fitting scene art, readable
characters when appropriate, responsive simultaneous controls, real hit feedback,
fair damage, meaningful requested skills/upgrades and complete pause/loss/retry flows.
Respect abstract puzzles and minimal requests; do not add shooting or skills to them.
Inspect actual workflow states on desktop and phone, including forms/results or
active play. Repair the largest concrete visible weaknesses, then rebuild and rerun
affected workflows. Compilation, functional behavior, layout and screenshot judgment
are separate evidence. Save passing checks against the exact source fingerprint;
verification infrastructure failure must preserve the implementation for retry.
Never call a build polished on the strength of a title screen or visible buttons.
'''


def delivery_playbook(brief):
    family = (brief.get('experienceBlueprint') or {}).get('family') or brief.get('productType', 'website')
    return {
        'version': 1, 'family': family, 'standard': 'Apply the shared DELIVERY CRAFT STANDARD throughout planning, implementation and review.',
        'stateContract': ['Entry and primary task', 'Actual action and visible outcome',
                          'Requested detail/result and return path', 'Invalid, empty and recovery states where relevant',
                          'Reload continuity where persistence is required'],
        'reviewEvidence': ['Opening composition at desktop and phone widths',
                           'Real workflow states captured after executed input and an outcome assertion',
                           'Phone action reachability, readable hierarchy and no horizontal overflow',
                           'Separate build, functional, geometry and screenshot-review results'],
        'scope': 'Apply the craft process to the requested product; preserve explicit style, genre, minimal scope and working saved data.',
    }
