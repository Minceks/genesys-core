"""Purpose-specific depth for every generated product, without a model request."""
import re


BLUEPRINTS = {
    'commerce': {
        'journey': ['Discover relevant products', 'Inspect and compare useful information', 'Choose quantity and manage a saved cart', 'Validate checkout and revisit the honest pending order'],
        'capabilities': ['Search, category filters and sorting suited to catalog size', 'Useful product details and saved items', 'Comparison where differences aid a decision', 'Editable cart, totals and local order history'],
        'visual': 'Product-led art direction, substantial merchandise imagery, curated sections and consistent detail/cart/form styling.',
    },
    'portfolio': {
        'journey': ['Understand the creator and their specialty', 'Explore relevant work', 'Open a substantial case study or project', 'Reach a truthful contact destination and return to browsing'],
        'capabilities': ['Work categories where the collection benefits from filtering', 'Real project details with problem, process and outcome', 'Accessible next/previous work navigation', 'A working contact destination or validated local inquiry with delivery clearly deferred'],
        'visual': 'Original image-led composition, distinct work imagery, editorial project narratives and deliberate mobile crops; avoid repeating one graphic as every project.',
    },
    'booking': {
        'journey': ['Discover and inspect a service', 'Choose a real available option and future date/time', 'Enter details and review the selection', 'Confirm, revisit and cancel or change the specific local reservation'],
        'capabilities': ['Useful service details and duration/pricing when supplied', 'Dependent date/time choices and unavailable states', 'Validation and a persistent confirmation', 'Reachable local reservation management and cancellation'],
        'visual': 'A polished service-discovery page and focused booking steps; clear selected state and readable review summary on phone.',
    },
    'dashboard': {
        'journey': ['Understand the relevant overview', 'Filter or search actual records', 'Inspect a meaningful breakdown or record', 'Perform the requested action and see all related views update'],
        'capabilities': ['Relevant date/category filters connected to metrics and charts', 'Record search, sort and contextual detail', 'Requested record actions with validation and persistence', 'CSV export of the displayed data when useful; label demo data'],
        'visual': 'Purposeful data density, legible units, one dominant analytical view and responsive record details; avoid decorative metric tiles.',
    },
    'editorial': {
        'journey': ['Discover useful content', 'Find a topic or search a substantial collection', 'Read a complete article', 'Continue to relevant content and navigate back'],
        'capabilities': ['Topic navigation and search when the content collection warrants it', 'Readable article/detail routes with real content', 'Related content and useful reading navigation', 'Saved reading only when useful; do not fake newsletter delivery'],
        'visual': 'Distinct editorial hierarchy, relevant feature imagery, readable article measure and varied story layouts.',
    },
    'documentation': {
        'journey': ['Understand the structure', 'Locate the right guide', 'Read or follow a complete example', 'Navigate related steps and recover from an empty search'],
        'capabilities': ['Structured topic navigation and content search', 'Readable guide/detail views and anchored sections', 'Working copy controls on actual examples where useful', 'Previous/next guidance and useful empty states'],
        'visual': 'Readable long-form typography, clear navigation and examples, restrained visual hierarchy and a usable phone menu.',
    },
    'business': {
        'journey': ['Understand the offering and its audience', 'Inspect relevant services, work or product information', 'Resolve practical questions', 'Complete the main inquiry or next-step action honestly'],
        'capabilities': ['Meaningful service/detail destinations beyond a hero', 'Relevant process, pricing or case-study information when supplied', 'Helpful FAQs and a reachable primary action', 'Validated inquiry or a real contact destination; external delivery remains separate'],
        'visual': 'Brand-specific first screen, substantial relevant imagery, varied sections, useful inner pages and a complete footer; no invented logos or testimonials.',
    },
    'game': {
        'journey': ['Understand controls and start', 'Play the actual core mechanic', 'Receive clear progress and failure/win feedback', 'Pause or restart and play again'],
        'capabilities': ['Playable core mechanic rather than a marketing shell', 'Useful HUD and feedback tied to game state', 'Pause/restart and responsive input', 'Safe touch controls and saved preferences/progress when appropriate'],
        'visual': 'Genre-specific scene and coherent art, animation and feedback; protect play space from obstructive decoration.',
    },
    'application': {
        'journey': ['Find or create the requested item', 'Inspect and act on that item', 'See meaningful validation and results', 'Revisit saved state, edit or reverse the action when appropriate'],
        'capabilities': ['A complete primary workflow with useful navigation', 'Search/filter when records need discovery', 'Meaningful detail and requested create/edit/delete actions', 'Validation, persistence, empty states and reversible recovery'],
        'visual': 'Task-specific navigation and density, clear hierarchy, consistent forms and detail states; use a workspace only when the task calls for one.',
    },
}


# Destinations describe visitor intent, not a mandatory route count or template.
DESTINATIONS = {
    'commerce': ['Storefront and collection discovery', 'Substantial product detail', 'Cart and checkout', 'Saved order and return to shopping'],
    'portfolio': ['Identity and curated work', 'Complete project case study', 'About and approach', 'Contact and return to work'],
    'booking': ['Service discovery', 'Service detail and selection', 'Booking and review', 'Confirmation and reservation management'],
    'dashboard': ['Overview tied to actual data', 'Record exploration', 'Contextual record or analytical detail', 'Requested action and updated results'],
    'editorial': ['Editorial front page', 'Topic discovery', 'Complete article', 'Related reading and return navigation'],
    'documentation': ['Guide index', 'Topic navigation and search', 'Complete guide and examples', 'Related and next steps'],
    'business': ['Brand and offering', 'Substantial service or work detail', 'About, process and practical questions', 'Contact or inquiry and result'],
    'game': ['Start and controls', 'Playable scene', 'Progress and outcome', 'Pause, restart and return'],
    'application': ['Purposeful home or workspace', 'Item discovery or creation', 'Contextual detail and requested actions', 'Saved result and recovery'],
}


def product_architecture(family):
    return {
        'destinations': list(DESTINATIONS[family]),
        'planning': 'For a full build, translate relevant destinations into named pages or purposeful views with a distinct content purpose, primary action and entry/return path. Record them in the build specification before implementation. Combine related destinations when appropriate; do not invent pages to meet a quota. Respect an explicitly requested single page or small tool. Targeted repairs preserve existing scope.',
        'navigation': 'Use real links for destinations, buttons for actions, a clear current location and usable phone navigation. Choose existing routing or hash navigation without unnecessary dependencies. Addressable detail destinations must open and reload correctly; preserve discovery context on return. Include a useful not-found/recovery state for implemented routes.',
        'presentation': 'Create a coherent branded shell and intentionally composed home, discovery, detail and action views as relevant. Public websites need visitor-facing navigation, substantive subject-specific content and a useful footer. Applications need a task-specific workspace, not an artificial marketing site. Tables belong where tabular data helps; a generic table, form or script output is not the entire product.',
        'content': 'Give each selected destination meaningful, audience-specific content and relevant verified imagery or honest original illustrations. Complete detail narratives, useful information and next steps; do not duplicate the same cards across nominal pages or use lorem ipsum, invented testimonials or unsupported claims.',
        'delivery': 'Deliver an actual runnable browser product with its JSX, responsive stylesheet, assets and working handlers. A code listing, shell script, generated source displayed as text, blank starter or instructions for the user to finish is not the requested website.',
        'review': 'Compare the built result with the chosen destination map. Reject an omitted primary journey, dead navigation, placeholder detail pages, a public site reduced to an administrative form/list, or source code shown instead of the product. Repair the missing experience within the selected scope. Keep subjective visual review separate from executable browser checks; never manufacture evidence.',
    }


def experience_blueprint(brief):
    product = brief.get('productType')
    # Preserve product identity on a repair; latest wording alone must not turn
    # a portfolio into a booking product or a dashboard into a marketing site.
    prompt = str(brief.get('originalRequest') or brief.get('latestRequest') or '')
    family = {'store':'commerce', 'portfolio':'portfolio', 'dashboard':'dashboard', 'game':'game'}.get(product)
    if family is None:
        if re.search(r'\b(booking|appointment|reservation|scheduling|salon)\b', prompt, re.I):
            family = 'booking'
        elif re.search(r'\b(documentation|knowledge base|help center|docs)\b', prompt, re.I):
            family = 'documentation'
        elif (brief.get('designResearch', {}).get('family') == 'gaming-editorial'
              or re.search(r'\b(blog|news|magazine|articles|editorial)\b', prompt, re.I)):
            family = 'editorial'
        else:
            family = 'application' if product == 'app' else 'business'
    blueprint = {
        'family': family,
        **BLUEPRINTS[family],
        'productArchitecture': product_architecture(family),
        'selectionPolicy': 'For a new full product or explicit feature expansion, select a coherent useful set from these capabilities for the actual audience, content and request. They are candidates, not mandatory features for every site. Targeted repairs keep their scope. Do not add administrative CRUD to an informational website.',
        'stateCoverage': ['Empty and populated content', 'Loading and recoverable errors where asynchronous work exists', 'Validation and success for each implemented form', 'Selected/filter state and sensible back navigation', 'Reload persistence for ordinary saved user data'],
        'completionStandard': 'A styled hero, repeated card grid or visible buttons alone are not a finished product. Implement the whole selected journey, useful inner views and appropriate content depth. Every enabled control must have a real result.',
        'visualReview': 'Review the first screen, content/detail views, forms, empty/populated states and navigation at desktop and phone sizes. Use purpose-appropriate composition, readable type, real subject imagery and restrained motion with reduced-motion support.',
        'integrationPolicy': 'Never invent testimonials, certifications, metrics or completed external operations. Browser-local state is not remote synchronization. Real authentication, shared data, payments and message delivery require actual integrations; label unavailable handoffs honestly.',
        'evidence': 'Write acceptance outcomes for the selected journey before implementing. Exercise real typing, action results, back navigation, reload, and edit/cancel/delete recovery where implemented; static visibility does not prove functionality.',
    }
    if re.search(r'\b(passwords?|credentials?|vault)\b', prompt, re.I):
        blueprint['sensitiveDataPolicy'] = ('If retaining passwords or credentials, require actual encrypted storage and an appropriate unlock design before claiming a secure vault. Ordinary localStorage hooks and masked inputs are insufficient. A prototype must clearly identify unencrypted demo storage and use synthetic values; functional UI verification is not a security audit.')
    geographic = re.search(r'\b(geographic|geolocation|gps|hiking|trails?|nearby|latitude|longitude)\b', prompt, re.I)
    map_request = re.search(r'\b(maps?|mapping)\b', prompt, re.I)
    abstract_map = re.search(r'\b(mind|concept|site|road|game|level)\s*maps?\b|\bsitemap\b', prompt, re.I)
    if geographic or (map_request and not abstract_map):
        blueprint['geographicMapPolicy'] = {
            'rendering': 'Use a real geographic basemap with a supported mapping library/provider, actual latitude/longitude, visible attribution and loading/error recovery. An SVG sketch, random points or decorative polyline does not satisfy a geographic map request.',
            'location': 'Use the requested real place or the user-selected working area. For user-relative maps offer an explicit Use my location action, browser permission and manual map/coordinate selection when denied, unavailable or working elsewhere. Do not infer location from language, timezone or a made-up default. Clearly distinguish an unselected world overview from a selected area.',
            'data': 'Only draw trails, business locations or POIs from supplied or verified geographic data. Never convert illustrative x/y points into fabricated geographic routes, move a fixed trail to the user position, or claim a basemap alone provides nearby trails/routing. Explain missing route data at its point of use.',
            'privacy': 'Request device location only after an explicit user action; do not continuously track or persist precise device coordinates by default. Let users change or clear a selected area. Browser-local selection is not account synchronization.',
            'verification': 'Test known synthetic coordinates, permission granted/denied/timeout, manual selection, location changes, clearing, actual provider tiles, real pan/zoom and attribution at desktop/phone widths. Inspect the geographic center and overlays; loaded controls or a sample illustration alone do not verify a map. Provider outages remain visible and unverified.',
        }
    return blueprint
