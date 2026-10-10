"""Bounded initial source context shared with the model and provider fallbacks."""


class InspectionCache:
    def __init__(self, workspace):
        self.workspace = workspace
        self.reads = {}

    def read_file(self, path):
        if path not in self.reads:
            self.reads[path] = self.workspace.read_file(path)
        return self.reads[path]

    def __getattr__(self, name):
        return getattr(self.workspace, name)


def initial_source_context(cache, files, targets):
    available = set(files or [])
    priority = ['src/App.jsx', 'src/App.tsx', 'src/styles.css'] if '.genesys-user-project' in available else []
    candidates = list(dict.fromkeys(priority + list(targets or [])))
    parts = []
    remaining = 12000
    for path in candidates:
        if len(parts) >= 4 or path not in available or not path.endswith(('.jsx', '.tsx', '.css')) or path.startswith('recovered/'):
            continue
        result = cache.read_file(path)
        content = result.get('content') if isinstance(result, dict) else None
        if not isinstance(content, str) or result.get('status') != 'success' or result.get('truncated') or len(content) > min(6000, remaining):
            continue
        parts.append(f'FILE: {path}\n{content}\nEND FILE: {path}')
        remaining -= len(content)
    if not parts:
        return ''
    return ('ALREADY INSPECTED CURRENT SOURCE\nThese complete files were read from this project immediately before implementation. '
            'Do not read them again unless your edits changed them or additional context is needed. '
            'Begin implementation using this source. Batch independent edits into one tool-call response when possible.\n\n'
            + '\n\n'.join(parts))
