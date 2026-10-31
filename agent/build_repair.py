"""Mechanical build failures that need no model and no repair attempt."""
import re
from pathlib import PurePosixPath

MISSING_EXPORT = re.compile(r'"([^"]+)" is not exported by "([^"]+)", imported by "([^"]+)"')
BUILD_KILLED = 137


def default_import_fix(output, read):
    """Rewrite `import { X }` to `import X` when the target only has a default export."""
    found = MISSING_EXPORT.search(output)
    if not found or found[1] == 'default':
        return None
    name, target, importer = found.groups()
    if not re.search(r'^\s*export\s+default\b', read(target), re.M):
        return None
    source = read(importer)
    stem = PurePosixPath(target).stem

    def replace(match):
        names = [part.strip() for part in match[1].split(',') if part.strip()]
        chosen = next((part for part in names if re.split(r'\s+as\s+', part)[0] == name), None)
        if not chosen or PurePosixPath(match[3]).stem != stem:
            return match[0]
        local = re.split(r'\s+as\s+', chosen)[-1]
        rest = [part for part in names if part != chosen]
        return f"import {local}{', { ' + ', '.join(rest) + ' }' if rest else ''} from {match[2]}{match[3]}{match[2]}"

    fixed = re.sub(r'''import\s*\{([^}]*)\}\s*from\s*(['"])([^'"]+)\2''', replace, source)
    return (importer, fixed) if fixed != source else None
