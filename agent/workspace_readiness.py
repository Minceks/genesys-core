"""Prepare an editor workspace without tying saved-preview reads to its lifecycle."""


def sandbox_not_ready(error):
    message = str(error).casefold()
    code = str(getattr(error, 'code', '')).casefold()
    return ('sandbox_not_running' in message or 'sandbox_not_running' in code
            or 'failed to resolve container ip' in message)


def prepare_workspace(workspace):
    prepare = getattr(workspace, 'prepare', None)
    if callable(prepare):
        prepare()
    else:
        # Older workspace adapters have only the lifecycle method.
        ensure = getattr(workspace, '_ensure_sandbox_running', None)
        if callable(ensure): ensure()
