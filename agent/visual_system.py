"""Concrete, overridable art direction shared by planning and implementation."""
import hashlib
import re

PALETTES = {
    'paper-ink': {'background': '#f5f3ee', 'surface': '#fffdf8', 'text': '#20251f', 'muted': '#596257',
                  'accent': '#345640', 'accentText': '#ffffff', 'border': '#d8ddd2'},
    'mineral': {'background': '#f1f4f5', 'surface': '#ffffff', 'text': '#172630', 'muted': '#52636d',
                'accent': '#234d63', 'accentText': '#ffffff', 'border': '#d3dde2'},
    'warm-clay': {'background': '#f7f0e7', 'surface': '#fffcf7', 'text': '#30251f', 'muted': '#706055',
                  'accent': '#9c432c', 'accentText': '#ffffff', 'border': '#e1d4c5'},
    'dark': {'background': '#111917', 'surface': '#1c2823', 'text': '#f2f5ed', 'muted': '#b6c4b9',
             'accent': '#c3d997', 'accentText': '#17200f', 'border': '#35453b'},
    'monochrome': {'background': '#f7f7f5', 'surface': '#ffffff', 'text': '#191919', 'muted': '#60605b',
                   'accent': '#252525', 'accentText': '#ffffff', 'border': '#d9d9d3'},
    'indigo': {'background': '#f8fafc', 'surface': '#ffffff', 'text': '#0f172a', 'muted': '#475569',
               'accent': '#4f46e5', 'accentText': '#ffffff', 'border': '#e2e8f0'},
    'emerald': {'background': '#fafafa', 'surface': '#ffffff', 'text': '#18181b', 'muted': '#52525b',
                'accent': '#047857', 'accentText': '#ffffff', 'border': '#e4e4e7'},
    'ember': {'background': '#fafaf9', 'surface': '#ffffff', 'text': '#1c1917', 'muted': '#57534e',
              'accent': '#c2410c', 'accentText': '#ffffff', 'border': '#e7e5e4'},
    'ocean': {'background': '#f8fafc', 'surface': '#ffffff', 'text': '#0c1a26', 'muted': '#475569',
              'accent': '#0369a1', 'accentText': '#ffffff', 'border': '#e2e8f0'},
}

# Bundled with new projects, so pages never depend on a remote font service.
FONTS = {
    'inter': ('"Inter Variable", system-ui, sans-serif', '@fontsource-variable/inter'),
    'jakarta': ('"Plus Jakarta Sans Variable", system-ui, sans-serif', '@fontsource-variable/plus-jakarta-sans'),
    'grotesk': ('"Space Grotesk Variable", system-ui, sans-serif', '@fontsource-variable/space-grotesk'),
    'fraunces': ('"Fraunces Variable", Georgia, serif', '@fontsource-variable/fraunces'),
}


def visual_system(project_id, product, prompt, strategy):
    seed = int.from_bytes(hashlib.sha256(f'{project_id}:{product}'.encode()).digest()[:4], 'big')
    palette_name = ('dark' if re.search(r'\b(?:dark|night|black background)\b', prompt, re.I)
                    else 'monochrome' if re.search(r'\b(?:monochrome|black and white)\b', prompt, re.I)
                    else 'warm-clay' if re.search(r'\b(?:warm|earthy|terracotta)\b', prompt, re.I)
                    else 'paper-ink' if strategy.get('direction') in {'editorial', 'magazine'}
                    else ('indigo', 'emerald', 'ember', 'ocean')[seed % 4])
    public = product in {'website', 'portfolio', 'store'}
    editorial = public and strategy.get('direction') in {'editorial', 'boutique', 'premium', 'magazine'}
    display = FONTS['fraunces' if editorial else ('jakarta', 'grotesk', 'inter')[(seed >> 8) % 3]]
    body = FONTS['inter']
    tokens = dict(PALETTES[palette_name])
    # Named accents are a common explicit preference; apply them to actual tokens
    # instead of merely asking the implementation to override an unrelated palette.
    accents = [(r'\b(?:cobalt|indigo|blue)\b', '#3057d5'),
               (r'\b(?:teal|turquoise)\b', '#0e6c6d'),
               (r'\b(?:coral|terracotta)\b', '#b74832'),
               (r'\b(?:plum|purple)\b', '#743d70')]
    for pattern, color in accents:
        if re.search(pattern, prompt, re.I):
            tokens.update(accent=color, accentText='#ffffff')
            break
    return {
        'version': 1,
        'priority': 'Existing brand tokens, explicit user preferences and supplied references override every fallback below. '
                    'These are a coherent starting system, not a requirement to recolor an existing product.',
        'palette': {'name': palette_name, 'tokens': tokens,
                    'usage': 'Use the accent mainly for primary actions and selected states. Alternate quiet surface tones; '
                             'avoid unrelated colored sections, arbitrary gradients and a shadow around every block.'},
        'type': {
            'displayFamily': display[0],
            'bodyFamily': body[0],
            'packages': list(dict.fromkeys((display[1], body[1]))),
            'hero': 'clamp(2.5rem, 6vw, 5.5rem)' if public else 'clamp(1.75rem, 3vw, 2.75rem)',
            'section': 'clamp(1.75rem, 3vw, 3rem)' if public else 'clamp(1.25rem, 2vw, 1.75rem)',
            'body': '1rem', 'bodyLeading': 1.65, 'headingLeading': 1.05,
            'headlineWidth': '14ch' if public else '24ch', 'bodyWidth': '62ch',
            'usage': 'Create contrast between display, headings, body and labels. Use deliberate line breaks and '
                     'balanced wrapping; never force a short headline into a narrow unreadable column. '
                     'These fonts are bundled with new projects and fall back safely; remote fonts must not be required to render the page.'},
        'layout': {'maxWidth': '1240px' if public else '1440px', 'gutter': 'clamp(1rem, 4vw, 4rem)',
                   'sectionSpace': 'clamp(3.5rem, 8vw, 7rem)' if public else 'clamp(1.5rem, 3vw, 3rem)',
                   'spacingScale': [4, 8, 12, 16, 24, 32, 48, 64, 96],
                   'geometry': strategy.get('composition', ''),
                   'phone': 'Recompose at narrow widths: wrap the brand/header, stack the hero, retain readable '
                            'image crops, simplify navigation, and keep primary actions at least 44px high. '
                            'Use minmax(0, 1fr) and min-width: 0; do not conceal overflow to pass checks.'},
        'materials': {'controlRadius': '10px', 'panelRadius': '16px',
                      'usage': 'Use borders to organize information and one restrained shadow only for elevated overlays. '
                               'Let important images and text breathe; do not put every paragraph in a card.'},
        'imagery': 'The primary visual must communicate the actual product. Use provided images first. '
                   'Without reliable photography, draw a detailed, recognizable original subject illustration with '
                   'composition, depth and useful detail. A rectangle, circle, gradient or text saying Sample is '
                   'not a finished hero or product illustration. Preserve honest illustration/sample labeling.',
        'copy': 'Write specific headlines and useful details for the audience. Avoid generic welcome copy, '
                'invented reviews, sales counts, certifications, shipping promises and unsupported trust badges.',
        'execution': [
            'Choose one art direction and a specific first-screen focal point before writing JSX.',
            'Use the visual system through its theme utilities or shared CSS variables across sections, drawers and forms.',
            'Vary section geometry and image scale to support the content, rather than repeating identical cards.',
            'Finish desktop and phone composition, focus/hover/disabled states and reduced-motion behavior in the same draft.',
            'Review actual source against the brief: specific typography, aligned edges, balanced whitespace, relevant assets and complete interactions.',
        ],
    }
