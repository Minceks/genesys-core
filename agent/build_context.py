"""Bounded initial source context shared with the model and provider fallbacks."""

class InspectionBudget:
    """Bound exploration both before and after edits, including provider changes."""
    def __init__(self):
        self.count = 0
        self.has_edits = False
        self.repairing = False

    @property
    def limit(self): return 2 if self.has_edits or self.repairing else 4

    def tools(self, tools):
        if self.count < self.limit: return tools
        return [tool for tool in tools if tool['function']['name'] not in {'read_file','list_files'}]

    def inspect(self):
        if self.count >= self.limit: return False
        self.count += 1
        return True

    def edited(self):
        self.has_edits = True
        self.count = 0

    def repair(self):
        self.repairing = True
        self.count = 0


def verification_due(step, implementation_limit, changed, ready, repairing, remaining_seconds):
    from .progress import REVIEW_RESERVE_SECONDS
    return (changed and not ready and not repairing
            and (step > implementation_limit or remaining_seconds <= REVIEW_RESERVE_SECONDS))


def transient_provider_error(error):
    return isinstance(error, TimeoutError) or type(error).__name__ in {
        'APITimeoutError','APIConnectionError','ReadTimeout','ConnectTimeout'}

def tools_for_repair(tools, inspections):
    # Permit fresh targeted source after each successful edit, then require
    # implementation or a no-tool response so mandatory verification can run.
    if inspections < 2:
        return tools
    return [tool for tool in tools if tool['function']['name'] not in {'read_file', 'list_files'}]


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
    priority = ['src/App.jsx', 'src/App.tsx', 'src/styles.css', 'src/usePersistentState.js'] if '.genesys-user-project' in available else []
    candidates = list(dict.fromkeys(list(targets or []) + priority))
    parts = []
    remaining = 12000
    for path in candidates:
        if len(parts) >= 4 or path not in available or not path.endswith(('.js', '.jsx', '.tsx', '.css')) or path.startswith(('recovered/', 'src/components/ui/')):
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
