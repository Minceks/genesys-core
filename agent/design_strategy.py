"""Purpose-aware design options and repeatable redesign variation without model calls."""
import hashlib
import re


COMPOSITIONS = {
    'website': (
        ('editorial', 'Oversized editorial headline, asymmetric visual hero, alternating full-width stories, concise navigation and rich footer.'),
        ('immersive', 'Full-bleed relevant imagery, compact floating primary action, cinematic section transitions and focused content detail views.'),
        ('architectural', 'Precise split-screen hero, strong typographic grid, contrasting section backgrounds and a horizontal feature sequence.'),
        ('boutique', 'Warm tactile surfaces, expressive typography, curated visual narrative and a calm conversion journey.'),
    ),
    'portfolio': (
        ('gallery', 'Edge-to-edge photographic opening, varied image scales, restrained captions and immersive project details.'),
        ('magazine', 'Editorial cover, asymmetric photographic stories, oversized project names and sequential case studies.'),
        ('studio', 'Bold identity with a split image introduction, curated horizontal work strips and generous project pages.'),
    ),
    'store': (
        ('campaign', 'Campaign-led visual opening, curated collections, focused product detail and accessible basket drawer.'),
        ('catalogue', 'Compact discovery navigation, useful filters, large merchandise imagery and clear responsive product comparison.'),
        ('premium', 'Quiet product storytelling, ample whitespace, detail imagery and a minimal purchase journey.'),
    ),
    'dashboard': (
        ('workspace', 'Compact navigation rail, purposeful overview, meaningful chart area and task-focused detail drawer.'),
        ('operations', 'Top navigation, dense but readable activity stream, contextual actions and expandable record details.'),
        ('insights', 'Strong summary typography, spacious analytical canvas and progressive drill-down instead of repeated metric cards.'),
    ),
    'app': (
        ('focused', 'Single primary workflow, progressive disclosure, contextual detail and compact secondary navigation.'),
        ('workspace', 'Responsive split-pane workspace with a main task canvas, useful inspector and mobile bottom navigation.'),
        ('timeline', 'Activity or calendar-led workflow, clear next action, contextual forms and purposeful empty states.'),
    ),
    'game': (
        ('cinematic', 'Atmospheric playable world, layered scenery, lighting and a restrained legible HUD.'),
        ('graphic', 'Intentional stylized shapes, coherent character art, strong silhouettes and responsive input feedback.'),
        ('spatial', 'Depth-led playable scene, contextual HUD and clear camera/interaction affordances appropriate to the rendering stack.'),
    ),
}


def requests_redesign(prompt):
    return bool(re.search(
        r'\b(redesign|restyle|modernize|reimagine|new look|fresh look)\b|'
        r'\b(?:different|diferent|difrent|diffrent)\s+(?:ui|design|style|layout|look|website|site|app)\b|'
        r'\b(?:build|make|create)\s+(?:something\s+)?(?:different|diferent|difrent|diffrent)\b|'
        r'\b(?:ui|design|style|layout|look|website|site|app)\b.{0,30}\b(?:different|diferent|difrent|diffrent)\b',
        prompt, re.I,
    ))


def design_strategy(project_id, product, prompt, previous=None, redesign=False):
    options = COMPOSITIONS.get(product, COMPOSITIONS['website'])
    old = (previous or {}).get('designStrategy', {})
    revision = int(old.get('revision', 0)) + (1 if redesign else 0)
    seed = int.from_bytes(hashlib.sha256(f'{project_id}:{product}'.encode()).digest()[:4], 'big')
    index = (seed + revision) % len(options)
    if redesign and options[index][0] == old.get('direction'):
        index = (index + 1) % len(options)
    choices = [{'id': key, 'composition': layout} for key, layout in options]
    return {
        'revision': revision, 'direction': options[index][0],
        'composition': options[index][1], 'alternatives': choices,
        'selectionPolicy': 'Evaluate these distinct options against the audience, content and primary task. '
            'Use the recommended option or a better justified original composition. Explicit user preferences win.',
        'redesign': redesign,
        'previousDirection': old.get('direction') if redesign else None,
        'redesignRequirements': [
            'Change composition and section rhythm, not only copy or accent color.',
            'Choose a distinct typography hierarchy and asset treatment.',
            'Preserve working workflows, storage keys, data and accessible controls.',
            'Compare the implemented layout to the existing source before claiming a redesign.',
        ] if redesign else [],
        'capabilities': 'Choose purposeful multi-view navigation, galleries, detail drawers, calendars, '
            'maps or diagrams, filtering, responsive workspaces and interactive scenes when they serve '
            'the request. Use installed tools; do not add features merely to fill a template. '
            'Real payments, accounts, shared data and external delivery require working integrations.',
        'finishCriteria': [
            'Distinct first-screen focal point and meaningful content hierarchy.',
            'Consistent design tokens, refined typography, spacing, imagery and original identity.',
            'Complete hover, focus, selected, loading, empty, error and success states.',
            'Intentional mobile composition and reachable primary actions.',
            'Every presented action has a real outcome; no fake success or placeholder views.',
        ],
    }
