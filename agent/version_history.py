"""Sandbox source history, separate from verified/published revisions."""
import json
from pathlib import Path
import shlex
import hashlib
import os


def storage(project_id):
    return Path(os.getenv('RAILWAY_VOLUME_MOUNT_PATH') or '.genesys-data')/'source-history'/hashlib.sha256(project_id.encode()).hexdigest()


def local_versions(project_id):
    from .version_worker import versions
    return [{k:v for k,v in record.items() if k!='hashes'} for record in versions(storage(project_id))]


def restore_after_sandbox_loss(workspace, *, created=False):
    """Restore saved source only into a newly created sandbox or pending recovery.

    Pin the selected version before backing up the fresh starter. On a failed
    restore, retry that same version rather than selecting the starter backup.
    This restores source, never publication or browser-verification status.
    """
    from .daytona_workspace import REMOTE_PROJECT_ROOT
    import re
    marker = str(Path(REMOTE_PROJECT_ROOT).parent).replace('\\','/')+'/.genesys-source-recovery.json'
    check = workspace.sandbox.process.exec('test -f '+shlex.quote(marker),timeout=10)
    if check.exit_code == 0:
        pending = json.loads(workspace.sandbox.fs.download_file(marker))
        if pending.get('projectId') != workspace.project_id or not re.fullmatch(r'[0-9a-f]{32}',str(pending.get('version',''))):
            raise RuntimeError('Invalid pending source recovery record')
        version = pending['version']
    elif created:
        records = local_versions(workspace.project_id)
        if not records:
            return None
        version = records[0]['id']
        workspace.sandbox.fs.upload_file(json.dumps({'projectId':workspace.project_id,'version':version}).encode(),marker)
    else:
        return None
    result = operate(workspace,'restore',id=version)
    cleaned = workspace.sandbox.process.exec('rm -f '+shlex.quote(marker),timeout=10)
    if cleaned.exit_code:
        raise RuntimeError('Source recovered but its pending marker could not be cleared')
    return result


def operate(workspace,action,**payload):
    from .workspace_readiness import prepare_workspace
    prepare_workspace(workspace)
    from .daytona_workspace import REMOTE_PROJECT_ROOT
    script=Path(__file__).with_name('version_worker.py').read_text(encoding='utf-8')
    remote=str(Path(REMOTE_PROJECT_ROOT).parent).replace('\\','/')+'/.genesys-version-history'
    project_id=workspace.project_id
    local=storage(project_id)
    if action=='restore':
        import re
        version=payload.get('id','')
        if not re.fullmatch(r'[0-9a-f]{32}',version):raise ValueError('Invalid source version')
        selected={}
        for extension in ('.json','.zip'):
            path=local/(version+extension)
            selected[extension]=path.read_bytes() if path.is_file() else workspace.sandbox.fs.download_file(remote+'/'+version+extension)
        # Persist the current state before any source restoration, even if the
        # sandbox subsequently disappears during the restore operation.
        operate(workspace,'capture',label='Before source restore (durable)')
        mkdir=workspace.sandbox.process.exec('mkdir -p '+shlex.quote(remote),timeout=15)
        if mkdir.exit_code:raise RuntimeError('Version restore preparation failed')
        for extension,content in selected.items():
            workspace.sandbox.fs.upload_file(content,remote+'/'+version+extension)
    result=workspace.sandbox.process.exec('python3 -c '+shlex.quote(script)+' '+
        shlex.quote(REMOTE_PROJECT_ROOT)+' '+shlex.quote(action)+' '+shlex.quote(json.dumps(payload)),timeout=90)
    if result.exit_code!=0:
        raise RuntimeError('Project version operation failed. The published preview has not changed.')
    data=json.loads(result.result)
    record_id=data.get('id') if action=='capture' else data.get('backup') if action=='restore' else None
    if record_id:
        local.mkdir(parents=True,exist_ok=True)
        for extension in ('.zip','.json'):
            content=workspace.sandbox.fs.download_file(remote+'/'+record_id+extension)
            if len(content)>26_000_000:raise RuntimeError('Version persistence exceeds size limit')
            temp=local/(record_id+extension+'.tmp')
            temp.write_bytes(content);temp.replace(local/(record_id+extension))
        from .version_worker import versions
        total=0
        for index,record in enumerate(versions(local)):
            total+=record['bytes']
            if index>=30 or (index>0 and total>200_000_000):
                for extension in ('.json','.zip'):(local/(record['id']+extension)).unlink(missing_ok=True)
    return data
