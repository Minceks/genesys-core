"""Implement the saved visual system for untouched, independent new starters."""
import hashlib
import re

PATH = 'src/design-tokens.css'
PLACEHOLDER = '/* GeneSys design tokens: filled from the project brief before implementation. */\n'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def stylesheet(system):
    # Only plain values from the brief enter CSS; no arbitrary CSS fragments.
    def safe(value, fallback):
        return value if isinstance(value, str) and re.fullmatch(r'[\w\s#.,%()"\-]+', value) else fallback
    palette = system.get('palette', {}).get('tokens', {})
    typography = system.get('type', {})
    geometry = system.get('layout', {})
    materials = system.get('materials', {})
    defaults = {'background':'#f7f7f5','surface':'#ffffff','text':'#191919','muted':'#60605b',
                'accent':'#252525','accentText':'#ffffff','border':'#d9d9d3'}
    tokens = {name: value if re.fullmatch(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})', str(value)) else defaults[name]
              for name, value in ((key, palette.get(key, value)) for key,value in defaults.items())}
    declarations = [f'  --{name}: {value};' for name,value in tokens.items()]
    declarations += [
        '  --accent-text: var(--accentText);',
        f'  --font-display: {safe(typography.get("displayFamily"), "system-ui, sans-serif")};',
        f'  --font-body: {safe(typography.get("bodyFamily"), "system-ui, sans-serif")};',
        f'  --type-display: {safe(typography.get("hero"), "clamp(2rem, 5vw, 4rem)")};',
        f'  --type-section: {safe(typography.get("section"), "clamp(1.5rem, 3vw, 2.5rem)")};',
        f'  --page-width: {safe(geometry.get("maxWidth"), "1240px")};',
        f'  --page-gutter: {safe(geometry.get("gutter"), "clamp(1rem, 4vw, 4rem)")};',
        f'  --section-space: {safe(geometry.get("sectionSpace"), "clamp(2rem, 5vw, 5rem)")};',
        f'  --radius-control: {safe(materials.get("controlRadius"), "10px")};',
        f'  --radius-panel: {safe(materials.get("panelRadius"), "18px")};',
    ]
    return '/* Project visual system. Override deliberately in styles.css; keep the shared import. */\n:root {\n' + '\n'.join(declarations) + '''
  --space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px;
  --space-6:24px; --space-8:32px; --space-12:48px; --space-16:64px;
}
:where(body){background:var(--background);color:var(--text);font-family:var(--font-body);font-size:1rem;line-height:1.65}
:where(h1,h2,h3,h4){font-family:var(--font-display);line-height:1.12;text-wrap:balance}
:where(h1){font-size:var(--type-display);letter-spacing:-.04em}
:where(h2){font-size:var(--type-section);letter-spacing:-.025em}
:where(button){border:1px solid var(--border);border-radius:var(--radius-control);padding:10px 16px;background:var(--surface);color:var(--text);min-height:44px;cursor:pointer}
:where(input:not([type=checkbox]):not([type=radio]):not([type=hidden]),select,textarea){border:1px solid var(--border);border-radius:var(--radius-control);padding:10px 12px;background:var(--surface);color:var(--text);min-height:44px}
:where(input[type=checkbox],input[type=radio]){width:1.1rem;min-width:1.1rem;height:1.1rem;flex-grow:0;accent-color:var(--accent)}
:where(button,a,input,select,textarea):focus-visible{outline:3px solid var(--accent);outline-offset:3px}
'''


def prepare_foundation(workspace, system, previous=None):
    try:
        main = workspace.read_file('src/main.jsx').get('content', '')
        current = workspace.read_file(PATH).get('content', '')
    except (FileNotFoundError, ValueError, TypeError, AttributeError):
        return None
    if not re.search(r'''import\s*['"]\./design-tokens\.css['"]''', main):
        return None  # Existing projects are never migrated implicitly.
    recorded = (previous or {}).get('designFoundation') or {}
    if current != PLACEHOLDER and digest(current) != recorded.get('hash'):
        return {'path': PATH, 'status': 'user-managed'}
    css = stylesheet(system)
    if css != current:
        from .builder_controls import assert_writable
        try:
            assert_writable(workspace.project_id, PATH)
        except ValueError:
            return {'path': PATH, 'status': 'frozen'}
        result = workspace.write_file(PATH, css)
        if result.get('status') != 'success':
            raise RuntimeError('Could not save the project visual system stylesheet')
    return {'path': PATH, 'status': 'generated', 'hash': digest(css)}
