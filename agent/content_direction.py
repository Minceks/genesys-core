"""Keep visual style subordinate to the requested business and subject."""
import re


DOMAINS = (
    ('vehicle-rental', r'\b(?:car|vehicle|auto|van|motorcycle)\s+(?:rental|rentals|hire)\b|\brent(?:ing)?\s+(?:a\s+)?car\b',
     'Vehicles and rental services',
     ['Vehicle-led hero', 'Fleet with accurate category, seats and rental prices',
      'Availability and pickup/dropoff workflow', 'Rental policies and branch information'],
     'Cars must be the primary visual subject. Compact, sedan, SUV and van images or illustrations must match their categories. '
     'Roads or scenery may support the scene, but cannot substitute for vehicles. Do not turn the product into tourism, nature or sightseeing.'),
    ('food', r'\b(restaurant|bakery|cafe|coffee shop|pizzeria)\b',
     'Food, menu and hospitality', ['Food-led presentation', 'Menu and prices', 'Hours and location', 'Requested order or reservation workflow'],
     'Use food and venue imagery suited to the actual cuisine; do not substitute unrelated generic landscapes.'),
    ('fashion', r'\b(fashion|clothing|apparel|boutique clothing)\b',
     'Clothing and fashion', ['Actual garment categories', 'Product detail and sizing', 'Collection browsing', 'Requested basket workflow'],
     'Images must match the garment, category and available variant. Do not use generic scenery as product photography.'),
    ('property', r'\b(real estate|property listing|properties for sale)\b',
     'Properties and living spaces', ['Property discovery', 'Listing details and honest sample status', 'Location and specifications', 'Real inquiry destination'],
     'Show buildings/interiors appropriate to the listing. Do not imply stock photos represent a verified address.'),
    ('wellness', r'\b(salon|spa|barber|massage|beauty studio)\b',
     'Services, practitioners and appointments', ['Service discovery', 'Clear prices and durations', 'Booking flow', 'Venue and practitioner information'],
     'Use imagery related to the actual service and space. Never imply a sample portrait depicts a real practitioner.'),
)

LANDSCAPE_SAMPLE_IDS = ('photo-1500534623283-312aade485b7',
                        'photo-1470071459604-3b5ec3a7fe05',
                        'photo-1441974231531-c6227db76b6e')


def content_direction(prompt, previous=None):
    for key, pattern, subject, sections, assets in DOMAINS:
        if re.search(pattern, prompt, re.I):
            return {'domain': key, 'primarySubject': subject, 'contentPriorities': sections,
                    'assetPolicy': assets,
                    'rule': 'Choose layout and art direction around this subject. A theme name never changes the industry. '
                    'Preserve this subject during redesign. Use accurately labeled original illustrations when photo contents are uncertain.'}
    if previous:
        return dict(previous)
    return {'domain': 'custom', 'primarySubject': prompt[:800],
            'rule': 'Infer the actual subject and audience from the request before choosing content and imagery. '
                    'Every main section and image must support that subject, not a generic theme.'}


def domain_asset_issues(sources, direction):
    if direction.get('domain') != 'vehicle-rental':
        return []
    issues = []
    for path, content in sources.items():
        if isinstance(content, str) and any(asset in content for asset in LANDSCAPE_SAMPLE_IDS):
            issues.append(f'{path}: known landscape sample photo is used in a vehicle-rental build. '
                          'Replace it with subject-confirmed vehicle imagery or accurate labeled vehicle illustrations. '
                          'Match each fleet category, preserve rental workflows and remove unrelated nature/sightseeing content.')
    return issues
