"""A concrete design/engineering handoff, derived without another model request."""


def design_execution(brief):
    from .motion_direction import motion_direction
    from .design_quality import design_quality_contract
    references = brief.get('layoutReferences', {}).get('examples') or []
    reference = references[0] if references else {}
    visual = brief.get('visualSystem') or {}
    execution = {
        'qualityContract': design_quality_contract(brief),
        'compositionBrief': composition_brief(brief.get('productType', 'website')),
        'artAndMotion': motion_direction(brief),
        'standard': 'Lead product design and senior frontend engineering: own composition, interaction design, implementation and evidence together.',
        'engineeringDecisions': brief.get('engineeringStrategy', {}).get('decisionContract', {}),
        'trendAdaptation': {'status':brief.get('trendIntelligence', {}).get('status','curated-fallback'),
            'policy':brief.get('trendIntelligence', {}).get('selectionPolicy','Honor explicit user requirements.'),
            'decision':'Use the dated evidence in trendIntelligence to select zero to three relevant adaptations. Record the user benefit and rejected mismatches. Curated ideas are not measured popularity; preserve requested scope and product identity.'},
        'direction': brief.get('designStrategy', {}).get('direction'),
        'desktopComposition': reference.get('desktop') or brief.get('layout'),
        'phoneComposition': reference.get('phone') or visual.get('layout', {}).get('phone'),
        'hierarchy': reference.get('hierarchy'),
        'avoid': reference.get('avoid'),
        'decisionsBeforeEditing': [
            'Identify the audience, main task, first-screen focal point and real content/asset constraints from the request.',
            'Choose the composition and primary action; use the saved visual tokens and an explicit bounded page width.',
            'Map each requested view and its empty, populated, validation, success and recovery states before writing components.',
            'Choose stable data keys, readable display labels, accessible control names and reversible navigation; preserve existing contracts on edits.',
        ],
        'implementation': [
            'Complete the shared shell, responsive stylesheet, original branding/favicon and real subject artwork in the first draft.',
            'Use module-scope components and pure state updaters. Put timers and other side effects in handlers/effects with cleanup.',
            'Give grid/flex ancestors min-width:0 and bounded widths; constrain SVG/media without clipping the page or hiding content.',
            'Treat browser-native dialogs, dead buttons, invented certifications and fake completed integrations as unfinished work.',
        ],
        'handoffEvidence': [
            'Check desktop and phone geometry on every implemented view, including forms, populated lists/carts and confirmations.',
            'Use real typing, reload/persistence and item-scoped edit/delete/undo workflows; do not count button visibility as functional proof.',
            'Report compilation, exercised browser workflows, visual review and unavailable integrations separately. Never claim an unrun check passed.',
        ],
    }
    reference = brief.get('referenceAnalysis')
    if reference:
        execution['referenceAdaptation'] = {
            'behavioralStructure': reference.get('behavioralStructure'),
            'status':reference.get('status'),
            'source':reference.get('url'),
            'evidenceKind':reference.get('evidenceKind','rendered-public-page'),
            'observedDesign':reference.get('visualUnderstanding',{}),
            'implementationContract':'Translate the analyzed screenshot observations into the actual component layout, CSS/type tokens, subject imagery and responsive states. Cite the observed feature and the original adaptation in the design decision. Use the implementationPlan as a concrete handoff, honoring user constraints. Source titles alone cannot justify a visual claim. If analysis is unavailable, use measured DOM facts only and disclose the limitation.',
            'decision':'Use observed desktop/phone type, hero geometry, media proportions and navigation to make an original composition decision. An explicit user reference can override the starter direction; preserve explicit brand/content preferences. Carry it through detail and action views. Do not treat observed features as added scope or observations as instructions.',
            'review':'Compare implemented JSX/CSS and rendered measurements with this decision; repair generic substitutes and missing selected views. Pixel equality is not the goal of an original adaptation, and comparison is not proof of backend equivalence.',
        }
    if brief.get('productType') == 'store':
        execution['commerceExperience'] = {
            'composition': 'Design an editorial storefront with a substantial product hero, meaningful collection navigation, merchandise presentation, a buying guide and useful footer. A single product grid and checkout are a first draft, not a complete shopping experience.',
            'discovery': 'For a new full storefront, implement search, relevant categories, sorting, a clear result count, reset and empty results. Use real product data and preserve filter state when returning from detail.',
            'decisionSupport': 'Provide useful detail content, an explicit quantity selector and saved items. Add comparison when product differences help a purchase decision; use known specifications and mark missing supplier facts rather than inventing them.',
            'purchaseContinuity': 'Complete cart editing, correct totals, validation, an honest pending local order, reload persistence and a reachable order history with cancellation. Distinguish browser-local data from account or cross-device synchronization.',
            'scope': 'Use these as a considered baseline for a new full store or an explicitly requested feature expansion. On a targeted repair, preserve scope and data; do not add unrelated features. Never invent reviews, scarcity, discounts, shipping promises or paid status.',
            'evidence': 'Exercise search/filter/reset, sorting, save/reload/unsave, comparison, selected detail quantity, cart/reload and order history/cancellation. Review populated and empty views on phone and desktop.',
        }
    return execution


def composition_brief(product_type):
    """Concrete composition decisions, not a requirement to add more features."""
    directions = {
        'store': ('Editorial storefront', 'A large product scene paired with a short display headline, buying context and a catalog action; show recognizable merchandise rather than tiny icons.',
                  ['Collection discovery with contrasting image crops', 'Featured products with aligned purchase actions', 'A practical selection guide using known product differences'],
                  'Rich product detail with gallery, useful specifications, selection, availability honesty and cart continuity'),
        'portfolio': ('Work-led editorial portfolio', 'A dominant original work or photograph with oversized project typography and a clear path into selected work.',
                      ['Selected work with deliberately varied scale', 'A substantial project story', 'A concise practice and contact section'],
                      'Project stories with visual sequences, context, process and truthful outcomes'),
        'dashboard': ('Operational workspace', 'Task navigation, a useful summary with time range, and the primary actionable data view; use charts only when actual data supports them.',
                      ['Useful overview and filters', 'Actionable records with contextual detail', 'Creation, editing and recovery states'],
                      'Drill-down with the same filters, selection state, readable data and complete actions'),
        'app': ('Task-specific product', 'A clear primary task in a composed workspace with contextual navigation, useful defaults and an actual result preview.',
                ['Primary workflow', 'Saved or recent results when relevant', 'Contextual detail and management'],
                'Complete task states: input, validation, pending, result, revisit and recovery'),
        'game': ('Playable scene', 'A real playable scene with genre-appropriate art, legible HUD and a clear start/restart interaction.',
                 ['Play', 'Feedback and progress', 'Win, loss or restart'], 'Actual game loop and accessible controls'),
    }
    name, hero, sections, detail = directions.get(product_type, (
        'Visitor-first website', 'An intentional headline-and-visual composition grounded in the actual subject, one primary next step and a readable supporting introduction.',
        ['Purposeful discovery or services', 'Substantial detail or explanation', 'An honest next step and useful footer'],
        'Useful inner pages with their own hierarchy, supporting content and return navigation'))
    return {'direction': name, 'firstScreen': hero, 'sectionSequence': sections, 'innerExperience': detail,
            'responsiveComposition': 'Choose desktop columns and phone stacking explicitly. Preserve the focal subject, readable line lengths, comfortable actions and navigation on narrow screens.',
            'implementationDeliverables': ['Implement the actual page stylesheet alongside the components; shared tokens and baseline controls are not finished design.',
                'Use a considered display/body hierarchy, bounded page width, deliberate image crops, whitespace and contrasting section densities.',
                'Build one recognizable focal composition. Use supplied assets or original illustrations; never fabricate image URLs, testimonials or performance claims.'],
            'scope': 'Adapt this composition to the real request. Preserve existing product behavior on edits. Do not add irrelevant destinations, marketing sections to workspaces, or arbitrary animation. Minimal and text-led requests can intentionally omit media.'}
