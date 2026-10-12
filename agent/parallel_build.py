"""Parallel drafts for clean new projects; all writes remain coordinator-owned."""
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

logger = logging.getLogger(__name__)


def parsed(text):
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0]
    # Accept a complete JSON draft followed by explanatory prose. File ownership
    # validation below remains mandatory; never accept a second JSON payload.
    value, end = json.JSONDecoder().raw_decode(text)
    trailing = text[end:].strip()
    if trailing.startswith(('{', '[')):
        raise ValueError('Worker returned multiple JSON payloads')
    if not isinstance(value, dict):
        raise ValueError('Worker response must be an object')
    return value


def draft_project(prompt, source, provider_for, deadline):
    started = time.monotonic()
    if deadline - started < 100:
        return None
    planner = provider_for('openai')
    plan = parsed(planner.generate([{'role':'system', 'content':
        'Plan a React user application. Return JSON only: {"interface": "...", "requirements": [...], "pageComposition": [...]}. '
        'Follow presentationContract in the supplied design brief. For public websites plan a visitor-first '
        'hero, navigation, varied content sections, detail destinations and footer. Do not invent CRUD features '
        'or make a spreadsheet the public experience. Describe the purpose and visual composition of each section. '
        'Define exact exports, arguments, returned state fields and action names for src/projectLogic.js. '
        'That module owns data and behavior; App.jsx owns JSX. Use only React and existing dependencies. '
        'Persistence must reuse src/usePersistentState.js. Keep the plan under 800 words.'},
        {'role':'user','content':prompt + '\nExisting starter:\n' + source}], []).text)
    if not isinstance(plan.get('interface'), str) or not isinstance(plan.get('requirements'), list):
        raise ValueError('Parallel plan is missing its interface')
    if '"mode": "public-website"' in source:
        composition = plan.get('pageComposition')
        if not isinstance(composition, list) or len(composition) < 3:
            raise ValueError('Public website plan is missing its page composition')
    shared = prompt + '\nSHARED PLAN:\n' + json.dumps(plan) + '\nSTARTER:\n' + source
    def worker(name, paths, role):
        result = parsed(provider_for(name).generate([{'role':'system','content':
            role + ' Follow the exact shared interface. Return JSON only: {"files": {"path": "complete source"}}. '
            'Write only these assigned files: ' + ', '.join(paths) + '. No placeholders or dependencies. '
            'Use JavaScript, plain CSS and React. Keep each file compact. No build or deployment tools.'},
            {'role':'user','content': shared}], []).text)
        files = result.get('files')
        if not isinstance(files, dict) or set(files) != set(paths):
            raise ValueError('Worker violated file ownership')
        if any(not isinstance(code, str) or not code.strip() or len(code) > 50000 for code in files.values()):
            raise ValueError('Worker returned invalid source')
        return files
    # Workers create drafts in memory. They cannot concurrently modify the sandbox.
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix='genesys-builder') as pool:
        ui = pool.submit(copy_context().run, worker, 'openai', ['src/App.jsx','src/styles.css'],
            'Build the responsive UI. Import logic from ./projectLogic and styles from ./styles.css. '
            'Use a static named import of the shared hook and call it unconditionally at component top level. '
            'Never duplicate logic with fallback hooks, stubs or no-op actions. Never dynamically swap hooks. '
            'Render every requested action result, including quiz questions, answers and scores when applicable. '
            'Use in-page status and confirmation UI; never window alert, confirm or prompt. '
            'Complete a visual polish pass: purposeful composition, clear typography scale, consistent '
            'spacing, relevant imagery, finished control states and intentional mobile layouts. '
            'A visitor-facing portfolio must lead with photography, not editing forms or CRUD panels. '
            'Use the existing design guidance. For photography portfolios include real sample photo URLs '
            'Follow the presentationContract and pageComposition: public websites need a composed hero, '
            'navigation, varied purposeful sections, content details and footer. Keep management tools '
            'in a separate view when requested; do not lead with tables, data-entry forms or admin buttons. '
            'with alt text, responsive dimensions and clear sample labeling.')
        logic = pool.submit(copy_context().run, worker, 'gemini', ['src/projectLogic.js'],
            'Implement the exact shared logic interface, state, validation and requested actions. '
            'Preserve reload persistence using the supplied usePersistentState hook. No JSX or CSS.')
        files = {**ui.result(), **logic.result()}
    app = files['src/App.jsx']
    if 'import(' in app and 'projectLogic' in app:
        raise ValueError('UI must statically connect the shared logic module')
    if any(name in app for name in ('stubUseProjectLogic', 'stubUse', 'window.alert(', 'window.confirm(', 'window.prompt(')):
        raise ValueError('UI draft contains fallback logic or blocked browser dialogs')
    if re.search(r'\b(?:alert|confirm|prompt)\s*\(', app):
        raise ValueError('UI must use visible in-page feedback and confirmation')
    if re.search(r'\bfunction\s+useProjectLogic\b|\b(?:const|let)\s+useProjectLogic\s*=', app):
        raise ValueError('UI must use the shared hook rather than duplicate it')
    if time.monotonic() >= deadline:
        return None
    logger.info('parallel_drafts_ready duration_seconds=%.1f files=%d', time.monotonic()-started, len(files))
    return files
