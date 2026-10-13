"""Original layout blueprints: practical geometry, hierarchy and phone adaptations."""
import re


BLUEPRINTS = {
    'editorial-cover': {
        'fits': ['website', 'portfolio'],
        'desktop': '12-column grid: headline spans 5 columns, meaningful visual spans 7. Follow with a full-width story, then alternating 7/5 sections.',
        'phone': 'Single-column headline then visual; shorten headline line length, keep the CTA beside supporting copy, alternate imagery and concise details.',
        'hierarchy': 'One large headline, one primary CTA, quiet eyebrow and secondary navigation. Use a contrasting display face only if available.',
        'avoid': 'Repeated equal-sized cards and three competing primary buttons.',
    },
    'immersive-showcase': {
        'fits': ['website', 'portfolio', 'store'],
        'desktop': 'Relevant full-bleed visual with readable foreground copy; a compact task bar sits below it. Follow with staggered large showcase tiles and full detail views.',
        'phone': 'Use a portrait-aware crop and solid text surface if contrast is weak. Task bar becomes a short stacked form or opens a dedicated workflow.',
        'hierarchy': 'Subject imagery first, strong brand identity, concise value proposition and one obvious next action.',
        'avoid': 'Tiny thumbnail hero, unrelated photos, unreadable image overlays or a giant form covering the entire first screen.',
    },
    'boutique-story': {
        'fits': ['website', 'portfolio'],
        'desktop': 'Centered identity with an asymmetric photographic pair; narrative sections mix narrow text columns with broad visual space and a restrained contact finale.',
        'phone': 'Stack imagery in a deliberate sequence with different aspect ratios; keep captions attached to their images and contact action easy to reach.',
        'hierarchy': 'Warm coherent surfaces, expressive but readable headings and generous breathing room.',
        'avoid': 'Stock template slogans, decorative cursive body copy and decorative elements that obscure content.',
    },
    'product-discovery': {
        'fits': ['store', 'website'],
        'desktop': 'Compact navigation, curated feature story, category discovery, useful product filters and substantial product imagery. Detail views contain actual specifications and actions.',
        'phone': 'Two-column browsing when content allows; filters open an accessible sheet, details become a dedicated view and basket actions remain reachable.',
        'hierarchy': 'Consistent image ratios, readable prices and concise category labels; use visual storytelling above transactional detail.',
        'avoid': 'Fake checkout success, inconsistent photo subjects and inaccessible hover-only product actions.',
    },
    'task-workspace': {
        'fits': ['dashboard', 'app'],
        'desktop': 'Navigation rail approximately 220px wide; main task canvas uses the remaining space. Optional inspector 280-360px opens only when needed.',
        'phone': 'Navigation collapses to a labeled menu or bottom navigation; inspector becomes a detail view. Keep one obvious primary action.',
        'hierarchy': 'Clear task title, contextual toolbar, readable content density and purposeful state feedback.',
        'avoid': 'Marketing-sized hero, unused metric cards and shrinking desktop sidebars onto a phone.',
    },
    'calendar-service': {
        'fits': ['app', 'website'],
        'desktop': 'Separate service discovery from appointment selection. Booking view pairs useful context with date/slot selection and a clear review/confirmation step.',
        'phone': 'Progressive service → date/time → details → confirmation screens; preserve entered values between steps and provide a visible back action.',
        'hierarchy': 'Show available choices, selected state, validation near fields and persistent confirmation.',
        'avoid': 'Empty dependent dropdowns, calendar decoration without selectable slots and claiming a reservation was sent when only locally saved.',
    },
    'insight-canvas': {
        'fits': ['dashboard', 'app'],
        'desktop': 'Small summary strip, one dominant visualization, a useful supporting breakdown and contextual drill-down. Put charts near the questions they answer.',
        'phone': 'Prioritize summary then a simplified chart and expandable record details; maintain units and accessible chart descriptions.',
        'hierarchy': 'Readable numeric scale, restrained semantic color and fewer meaningful charts rather than a wall of tiles.',
        'avoid': 'Unlabeled demo statistics, tiny chart labels and misleading visual scales.',
    },
    'playable-world': {
        'fits': ['game'],
        'desktop': 'Main playable scene owns the viewport; lightweight HUD, deliberate start/pause screens and context-sensitive controls preserve visibility.',
        'phone': 'Landscape or portrait composition suits the genre; touch controls occupy safe edges and avoid covering essential game action.',
        'hierarchy': 'Strong silhouettes, coherent art direction, readable game state and immediate input feedback.',
        'avoid': 'Dashboard cards around the game, decorative 3D claims and controls unsupported by the actual renderer.',
    },
}


def layout_reference_library(product, prompt, strategy):
    candidates = [key for key, value in BLUEPRINTS.items() if product in value['fits']]
    if re.search(r'\b(booking|appointment|salon|reservation)\b', prompt, re.I) and 'calendar-service' in candidates:
        candidates.remove('calendar-service')
        candidates.insert(0, 'calendar-service')
    preferred = {
        'editorial': 'editorial-cover', 'magazine': 'editorial-cover',
        'immersive': 'immersive-showcase', 'gallery': 'immersive-showcase',
        'boutique': 'boutique-story', 'catalogue': 'product-discovery',
        'campaign': 'product-discovery', 'workspace': 'task-workspace',
        'operations': 'task-workspace', 'insights': 'insight-canvas',
        'timeline': 'calendar-service', 'cinematic': 'playable-world',
    }.get(strategy.get('direction'))
    if preferred in candidates:
        candidates.remove(preferred)
        candidates.insert(0, preferred)
    return {
        'version': 1,
        'evidence': 'Original curated composition blueprints, not observations of Wix or other live templates.',
        'examples': [{'id': key, **BLUEPRINTS[key]} for key in candidates[:3]],
        'implementationRules': [
            'Select a blueprint suited to the content; adapt it rather than copying a fixed page.',
            'Use minmax(0,1fr), min-width:0, fluid widths and explicit phone breakpoints. Never clip a fixed desktop layout to fit a phone.',
            'Use a coherent 4/8px spacing rhythm, readable line lengths and deliberate contrast between major and minor sections.',
            'A visual asset must match its title, category and purpose; label sample or illustrated assets honestly.',
            'Carry the design through detail views, forms, empty states, loading, errors and confirmation.',
        ],
    }
