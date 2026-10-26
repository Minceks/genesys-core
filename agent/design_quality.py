"""Shared product-aware design criteria for generation and screenshot review."""
from .engineering_strategy import SENIOR_ENGINEERING_STANDARD


BUILD_STANDARD = '''DEFAULT BUILD STANDARD: PREMIUM UI, USEFUL FUNCTIONS, SOLID ENGINEERING
Apply this standard to every new product, rebuild, redesign, edit and implementation repair.
UI: choose a subject-specific composition with deliberate typography, spacing, assets and
phone layout; carry the same finish through the requested detail, form and result states.
Functions: complete the selected user journey with real actions, appropriate validation,
useful empty/error/success states, persistence and recovery where the task needs them.
Engineering: use maintainable components, coherent state and data contracts, stable accessible
controls, safe handling of stored data, and the existing project's actual dependencies.
Do not substitute a static mockup, no-op controls or fake integration success for a working app.
For full builds choose a coherent, useful feature set from the product brief; do not deliver
only a hero and generic cards. For edits and repairs uphold this standard within the requested
scope and preserve working behavior, data keys and the user's visual preferences.
Verify compilation, real browser workflows and rendered design separately. A compile pass,
button visibility or an unrun check never proves a finished premium product. Missing evidence
remains unverified. Respect explicit minimal/text-led requests; quality is not feature count.
'''


BUILD_STANDARD += '\n' + SENIOR_ENGINEERING_STANDARD

FAMILY_FINISH = {
    'business': ('Brand and service story',
        'A subject-specific first impression, varied service/story sections and a clear inquiry path; carry the identity into service detail and forms.'),
    'commerce': ('Merchandise and purchase confidence',
        'Distinct recognizable merchandise, curated collection rhythm and useful buying context; catalog, detail and basket belong to the same visual system.'),
    'portfolio': ('Work and authorship',
        'Let substantial work imagery lead, vary project scale and crops, and design complete case-study narratives with restrained captions.'),
    'booking': ('Service and selection confidence',
        'Give services a credible visual identity and useful detail, then compose legible date/time selection, selected states and a calm review/confirmation.'),
    'dashboard': ('Analytical hierarchy',
        'One useful analytical focal view, aligned units and labels, purposeful data density and contextual record detail; decorative metric tiles do not create depth.'),
    'editorial': ('Story hierarchy and reading',
        'Distinguish lead and supporting stories through scale and layout, then provide a comfortable article measure, captions and related reading.'),
    'documentation': ('Orientation and comprehension',
        'Make navigation, guide typography, examples, callouts and search states coherent; a readable text-led composition is appropriate without a decorative hero.'),
    'application': ('Task and state clarity',
        'Compose around the actual task canvas, contextual controls and useful results; design populated, selected, empty and recovery states instead of decorating a generic form.'),
    'game': ('Scene and feedback',
        'Use coherent genre-specific scene art, clear silhouettes, legible HUD and visible interaction feedback; preserve play space and usable phone controls.'),
}


def design_quality_contract(brief):
    family = (brief.get('experienceBlueprint') or {}).get('family')
    if family not in FAMILY_FINISH:
        family = {'store': 'commerce', 'portfolio': 'portfolio', 'dashboard': 'dashboard',
                  'app': 'application', 'game': 'game'}.get(brief.get('productType'), 'business')
    focus, finish = FAMILY_FINISH[family]
    return {
        'version': 1, 'family': family, 'focus': focus, 'productFinish': finish,
        'deliveryStandard': BUILD_STANDARD,
        'definition': 'Premium means intentional, subject-specific composition and complete usable states. It is not a fixed palette, expensive animation or a luxury theme.',
        'criteria': [
            {'area': 'Identity and focal composition',
             'acceptance': 'The opening clearly communicates this product and its main task through specific content, deliberate type scale and a recognizable focal subject or useful task view.'},
            {'area': 'Content rhythm and depth',
             'acceptance': 'Supporting content has a purposeful hierarchy and changes density or geometry where content warrants it. A polished hero followed by repetitive default cards is unfinished.'},
            {'area': 'Typography and alignment',
             'acceptance': 'Display, headings, body and labels form a coherent hierarchy; line lengths, spacing, edges and image crops remain deliberate throughout the captured views.'},
            {'area': 'Assets and truthfulness',
             'acceptance': 'Every prominent visual matches its labeled subject. Use supplied or verified assets or detailed original illustration; no favicon substitutes, unrelated stock, invented testimonials or unsupported claims.'},
            {'area': 'Interaction finish',
             'acceptance': 'Navigation, filters, forms, detail and result states use the same visual language. Include clear selected, focus, disabled and recovery states where relevant; controls have real outcomes.'},
            {'area': 'Phone composition',
             'acceptance': 'Recompose the task and content at phone width with readable hierarchy, reachable navigation and actions, useful media crops and no clipping; shrinking desktop columns is insufficient.'},
        ],
        'execution': 'Before implementation choose the product-specific focal composition, supporting layout rhythm and asset treatment. Implement components, page CSS and real assets together, then inspect the rendered result against these same criteria.',
        'review': 'Review generated desktop and phone evidence beyond the opening screen. Cite concrete visible weaknesses and prioritize up to three repairs; passing geometry checks alone never proves premium quality.',
        'scope': 'Explicit user brand, references, minimal/text-led preferences and existing edit scope win. Apply quality within requested views; do not add arbitrary features, sections, integrations or animation. Preserve working behavior and stored data.',
    }
