"""Conservative routing for small presentation-only changes."""
import re
from .design_quality import BUILD_STANDARD


def focused_edit(prompt):
    if len(prompt.split()) > 70 or re.search(r'\b(build|create|new|redesign|rebuild|replace|integrat\w*|login|database|checkout|upload|image|photo|svg|logo|menu|handler|logic|state|broken|error|add\s+(?:a\s+)?(?:page|feature|component))\b', prompt, re.I):
        return False
    return bool(re.search(r'\b(change|adjust|update|make|increase|decrease|reduce|move|fix)\b', prompt, re.I)
                and re.search(r'\b(color|colour|font|spacing|padding|margin|header|footer|button|headline|title|border|radius|background|text|copy)\b', prompt, re.I))


def guidance(prompt):
    if not focused_edit(prompt):
        return ''
    return (BUILD_STANDARD + '\nFOCUSED PRESENTATION EDIT\nInspect the current component and the stylesheet rules that affect it. '
            'Use exact edit_file patches; whole-file replacement and new files are unavailable for this narrow request. '
            'Preserve routes, state, persistence, event handlers, assets and unrelated visual tokens. '
            'Use at most the relevant component and stylesheet unless a dependency requires another file. '
            'Do not generate a new product specification or redesign an existing application for this edit. '
            'Finish after the requested patch; the normal build and regression checks still run.')
