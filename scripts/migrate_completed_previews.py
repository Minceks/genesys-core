"""One-time, idempotent export of existing verified snapshots; no AI calls."""
import json
from agent.beta_storage import connection
from agent.preview_hosting import available_url, save, root
from agent.daytona_workspace import get_daytona, get_workspace, sandbox_name_for_project


def main(projects=None, refresh=False):
    with connection() as db:
        active = {row[0] for row in db.execute("SELECT project FROM jobs WHERE state IN ('queued','running')")}
        if projects is None:
            projects = [row[0] for row in db.execute(
                "SELECT DISTINCT project FROM jobs WHERE project NOT IN "
                "(SELECT project FROM jobs WHERE state IN ('queued','running')) LIMIT 100")]
    result = {'saved': [], 'alreadySaved': 0, 'skipped': []}
    for project in projects:
        if project in active:
            result['skipped'].append({'projectId': project, 'errorType': 'ActiveBuild'})
            continue
        if available_url(project) and not refresh:
            result['alreadySaved'] += 1
            continue
        try:
            # Do not create new sandboxes for deleted or expired projects.
            sandbox = get_daytona().get(sandbox_name_for_project(project))
            if str(sandbox.state).lower().endswith('archived'):
                result['skipped'].append({'projectId': project, 'errorType': 'ArchivedWorkspace'})
                continue
            workspace = get_workspace(project)
            workspace._ensure_sandbox_running()
            if refresh:
                # Preserve editable source alongside an operator-reviewed static
                # refresh. If backup fails, leave the existing preview active.
                from agent.version_history import operate
                operate(workspace,'capture',label='Source preserved before completed-preview refresh')
            save(workspace, project)
            result['saved'].append(project)
        except Exception as error:
            result['skipped'].append({'projectId': project, 'errorType': type(error).__name__})
    print(('PREVIEW_REFRESH_RESULT ' if refresh else 'MIGRATION_RESULT ') + json.dumps(result))
    report = 'preview-refresh-result.json' if refresh else 'preview-migration-v1.json'
    (root().parent / report).write_text(json.dumps(result), encoding='utf-8')
    return result


if __name__ == '__main__':
    main()
