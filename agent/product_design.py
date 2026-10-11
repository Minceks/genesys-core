"""Fast product classification and a persisted brief, without an extra model call."""
import json
import re

BRIEF_PATH = '.genesys-design.json'
PRODUCTS = {
    'game': r'\b(game|gaming|zombie|shooter|platformer|survival game)\b',
    'portfolio': r'\b(portfolio|photographer|photography)\b',
    'store': r'\b(store|shop|ecommerce|e-commerce|marketplace)\b',
    'dashboard': r'\b(dashboard|analytics dashboard|admin panel)\b',
    'app': r'\b(app|application|tracker|planner|task manager)\b',
    'website': r'\b(website|landing page|business site|blog|informational site)\b',
}
DIRECTIONS = {
    'game': {'layout':'Immersive playable scene with compact HUD, start/pause screens and mobile controls.',
        'visual':'Choose a world and genre appropriate atmosphere, depth, lighting, layered scenery, animated entities and readable HUD. Zombie survival calls for cinematic ruined environments, not portfolio cards or inherited brand styling.',
        'assets':'World scenery, character/enemy art or deliberate procedural graphics, hit effects and feedback.',
        'technology':'Use the existing rendering stack. For 2D/2.5D consider Canvas or an available game engine; for explicitly requested true 3D evaluate WebGL. Never claim a 2D canvas is full 3D.',
        'checks':['Start and restart the game', 'Movement/shooting or genre-specific inputs work', 'HUD updates and mobile controls are usable']},
    'portfolio': {'layout':'Image-led hero, project/gallery presentation, project detail and contact.',
        'visual':'Editorial typography, generous spacing and restrained colors that let the work dominate.',
        'assets':'Actual photos/artwork; use provided assets first and clearly label stock samples.',
        'technology':'Responsive React with an accessible gallery/lightbox when required.',
        'checks':['Images load', 'Gallery and detail interactions work', 'Contact actions have a real destination']},
    'store': {'layout':'Product discovery, filters, product detail, basket and checkout states.',
        'visual':'Clear merchandise hierarchy, consistent product imagery and prominent purchase actions.',
        'assets':'Relevant product photos and truthful product information.',
        'technology':'React storefront; payments and inventory require real backend integrations, not fake success.',
        'checks':['Product filters work', 'Basket quantities and totals update', 'Checkout integration status is accurate']},
    'dashboard': {'layout':'Navigation, summary metrics, meaningful charts, tables and filters.',
        'visual':'Readable data hierarchy, compact density, consistent units and restrained accent colors.',
        'assets':'Purposeful data visualizations; label demo data.',
        'technology':'React state and available chart libraries or semantic SVG; preserve data persistence.',
        'checks':['Filters update displayed data', 'Actions persist when appropriate', 'Empty and error states are usable']},
    'app': {'layout':'Organize screens around the primary user workflow and useful navigation.',
        'visual':'Clear interaction hierarchy, legible controls and purpose-specific styling.',
        'assets':'Use icons and imagery only where they help the workflow.',
        'technology':'React with appropriate state and persistence; shared data needs a backend.',
        'checks':['Primary workflow works', 'Validation and persistence work', 'Mobile navigation is usable']},
    'website': {'layout':'Purpose-specific page sections, clear navigation and a meaningful call to action.',
        'visual':'Brand and audience appropriate typography, coherent spacing and deliberate imagery.',
        'assets':'Relevant photos/illustrations, never empty image placeholders.',
        'technology':'Responsive semantic React/HTML with existing project dependencies.',
        'checks':['Navigation works', 'Calls to action work', 'Responsive sections do not overflow']},
}


def prepare_design(workspace, prompt):
    previous = None
    try:
        result = workspace.read_file(BRIEF_PATH)
        previous = json.loads(result.get('content', '')) if result.get('status') == 'success' else None
        if not isinstance(previous, dict) or previous.get('productType') not in PRODUCTS:
            previous = None
    except (FileNotFoundError, ValueError, TypeError, AttributeError):
        previous = None
    selected = next((name for name, pattern in PRODUCTS.items() if re.search(pattern, prompt, re.I)), None)
    replacement = bool(re.search(r'\b(build|create|make|replace|convert|turn|transform|redesign)\b', prompt, re.I))
    retain = previous and (not selected or selected == previous['productType'] or not replacement)
    if retain:
        brief = dict(previous)
        brief['latestRequest'] = prompt
        brief['designPolicy'] = 'Preserve the existing direction; apply explicit user changes only.'
    else:
        selected = selected or 'website'
        subtype = ('2.5D' if re.search(r'2[.]5d', prompt, re.I) else '3D' if re.search(r'\b3d\b', prompt, re.I) else '2D') if selected == 'game' else selected
        brief = {'version':1, 'productType':selected, 'subtype':subtype,
                 'originalRequest':prompt, 'latestRequest':prompt,
                 'designPolicy':'Choose a direction suited to this product. Explicit user preferences override recommendations.',
                 **DIRECTIONS[selected]}
        if previous:
            brief['purposeChangedFrom'] = previous['productType']
            brief['designPolicy'] += ' The product purpose changed; replace unsuitable inherited theme and layout.'
    brief['qualityStandard'] = {
        'composition': 'Distinctive focal point, purposeful section rhythm and product-appropriate density.',
        'typography': 'Coherent type hierarchy, readable body copy and deliberate line lengths.',
        'consistency': 'Shared spacing, color, border and control tokens; aligned visual edges.',
        'presentation': 'Show the user-facing product first; keep management tools out of visitor-facing hero content.',
        'responsive': 'Intentional phone layout, reachable actions, no hover-only functionality.',
        'finish': 'Real relevant imagery, concise copy, polished interaction states and preserved working behavior.',
    }
    saved = workspace.write_file(BRIEF_PATH, json.dumps(brief, ensure_ascii=False, indent=2))
    if not isinstance(saved, dict) or saved.get('status') != 'success':
        raise RuntimeError('Could not save project design brief')
    return brief
