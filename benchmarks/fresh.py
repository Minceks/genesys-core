"""Explicitly paid, isolated end-to-end builds; sequential workers share a USD ledger.

Run: python -m benchmarks.fresh --execute --max-usd 5 --output <new directory>
Never runs against an existing project. Raw logs/artifacts belong in gitignored evidence.
"""
import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'store': 'Build Paper Field, a polished stationery shop. Warm ivory, forest green, large editorial typography and original SVG product illustrations. Three clearly described notebooks with factual sample specifications, prices and product detail navigation. Detail quantity controls how many items are added. Cart supports quantity changes, removal, correct totals and reload/new-tab persistence. Checkout validates required name/email/address and creates a clearly labelled pending local order, confirmation and clears cart. No real payments, accounts, external services or invented certifications.',
    'portfolio': 'Build a polished illustrator portfolio for fictional artist Mara Sol. Cream and cobalt editorial art direction, striking typography and six original SVG artworks, labelled original sample illustrations. Include category filtering, clickable work detail dialogs with descriptions and accessible close controls, about section and contact link mailto:artist@example.test. A public welcoming portfolio, excellent phone and desktop layouts. No backend, accounts or outbound submissions.',
    'booking': 'Build Still Studio, a polished public website for a fictional ceramics workshop. Warm clay and cream, original SVG ceramics illustrations, generous editorial typography. Show three workshop offerings with durations and prices. Let visitors book a workshop by choosing offering, date/time, name and email, with required/email validation; show booking confirmation and a My bookings list with cancellation. Persist local bookings after reload. Clearly label this as a local demo with no payments, emails or server reservations. Responsive phone and desktop.',
    'dashboard': 'Build Focus Desk, a polished task dashboard for a fictional small design team. Calm light palette, indigo accents, clear type hierarchy and compact useful navigation. Seed three clearly sample tasks. Create a task with title, project and due date; edit it, mark complete, filter active/completed, delete it and show accurate counts. Persist every change after reload and in a new tab. Include useful empty states and required title validation. Excellent phone and desktop layouts. Local browser data only, no accounts or external services.'
}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, default=str), encoding='utf-8')


def worker(folder, case):
    # Set before importing settings, providers, database or workspace modules.
    os.environ.update(GENESYS_PROVIDER='openai', GENESYS_FALLBACK_PROVIDER='gemini',
        GENESYS_OPENAI_MODEL='gpt-5-mini', GENESYS_PARALLEL_BUILD='false',
        GENESYS_OUTPUT_TOKEN_LIMIT='6000', GENESYS_OUTPUT_TOKEN_CEILING='12000',
        GENESYS_JOB_DB=str(folder / 'benchmark.sqlite3'),
        GENESYS_DAILY_MODEL_TOKEN_BUDGET='10000000', GENESYS_BACKGROUND_TIMEOUT_SECONDS='600')
    from benchmarks.spend_guard import SpendGuard
    from agent import orchestrator, daytona_workspace as dw
    from agent.ai_provider import OpenAIProvider
    from agent.build_metrics import BuildMetrics, current
    from agent.progress import progress_callback
    from daytona import CreateSandboxFromSnapshotParams

    out = folder / case
    out.mkdir(exist_ok=True)
    identity = json.loads((out / 'identity.json').read_text())
    project = identity['projectId']
    manifest = json.loads((folder / 'manifest.json').read_text())
    guard = SpendGuard(folder / 'spend.json', manifest['modelLimitUsd'])
    base = OpenAIProvider(model='gpt-5-mini')
    create = base.client.chat.completions.create
    wrapped = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: guard.call(create, **kw))))
    # All fallback and planning paths use the same guarded API boundary.
    orchestrator.provider_for = lambda name: OpenAIProvider(model='gpt-5-mini', client=wrapped)

    def fresh_sandbox(self):
        if self.project_id != project:
            raise RuntimeError('Benchmark cannot open another project')
        sandbox = self.client.create(CreateSandboxFromSnapshotParams(
            name=self.name, language='javascript', ttl_minutes=20,
            auto_stop_interval=5, auto_delete_interval=0,
            labels={'purpose': 'genesys-fresh-benchmark', 'benchmark-project': project}), timeout=120)
        save(out / 'sandbox.json', {'id': sandbox.id, 'name': self.name,
             'cpu': sandbox.cpu, 'memory': sandbox.memory, 'disk': sandbox.disk})
        if (not 0 < sandbox.cpu <= 4 or not 0 < sandbox.memory <= 8
                or not 0 < sandbox.disk <= 100 or sandbox.gpu):
            sandbox.delete(timeout=60, wait=True)
            raise RuntimeError('Sandbox exceeds reserved infrastructure allowance')
        return sandbox

    dw.DaytonaWorkspace._get_or_create = fresh_sandbox
    metrics = BuildMetrics()
    current.set(metrics)
    progress_callback.set(lambda stage: save(out / 'progress.json', {'stage': stage, 'time': time.time()}))
    result = {}
    try:
        result = orchestrator.run_agent(CASES[case], project_id=project)
        selected = {k: result.get(k) for k in ('status', 'message', 'buildPassed',
            'browserVerified', 'verification', 'modifiedFiles', 'selfHealing')}
        selected['metrics'] = metrics.summary(result)
        save(out / 'result.json', selected)
        ws = dw.get_workspace(project)
        # Export only this synthetic app's public source/build; never .env or .git.
        for pattern in ('src', 'public', 'dist'):
            listing = ws.sandbox.process.exec(
                f'find {dw.REMOTE_PROJECT_ROOT}/{pattern} -type f 2>/dev/null', timeout=20)
            for remote in (listing.result or '').splitlines():
                prefix = dw.REMOTE_PROJECT_ROOT + '/'
                if not remote.startswith(prefix):
                    continue
                relative = Path(remote[len(prefix):])
                if '..' in relative.parts or any(p.startswith('.') for p in relative.parts):
                    continue
                target = out / 'app' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                data = ws.sandbox.fs.download_file(remote)
                target.write_bytes(data if isinstance(data, bytes) else data.encode())
        for name in ('package.json', 'index.html'):
            data = ws.sandbox.fs.download_file(dw.REMOTE_PROJECT_ROOT + '/' + name)
            (out / 'app' / name).write_bytes(data if isinstance(data, bytes) else data.encode())
    except Exception as error:
        # No credentials/signed preview URLs in the reviewable summary.
        save(out / 'error.json', {'type': type(error).__name__, 'metrics': metrics.summary(result)})
        raise
    finally:
        cleanup(out, project)


def cleanup(out, project):
    from agent.daytona_workspace import get_daytona, sandbox_name_for_project
    record = out / 'sandbox.json'
    if not record.exists():
        return
    info = json.loads(record.read_text())
    if info['name'] != sandbox_name_for_project(project):
        raise RuntimeError('Refusing cleanup of an unrelated sandbox')
    if (out / 'cleanup.json').exists():
        return
    from daytona.common.errors import DaytonaNotFoundError
    try:
        sandbox = get_daytona().get(info['id'])
    except DaytonaNotFoundError:
        save(out / 'cleanup.json', {'deleted': True, 'id': info['id'], 'confirmedAbsent': True})
        return
    if sandbox.name != info['name'] or sandbox.labels.get('benchmark-project') != project:
        raise RuntimeError('Sandbox ownership label does not match')
    sandbox.delete(timeout=60, wait=True)
    save(out / 'cleanup.json', {'deleted': True, 'id': info['id']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--max-usd', type=float)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prior-output', type=Path, action='append', default=[],
                        help='Previous suite evidence counted against the same total authorization')
    parser.add_argument('--worker', choices=CASES)
    args = parser.parse_args()
    folder = args.output.resolve()
    if args.worker:
        worker(folder, args.worker)
        return
    if not args.execute or args.max_usd != 5:
        parser.error('Explicit --execute --max-usd 5 required; $4 model cap + $1 infrastructure reserve')
    prior = Decimal('0')
    seen = set()
    for previous in args.prior_output:
        previous = previous.resolve()
        if previous in seen:
            parser.error('Duplicate prior budget ledger')
        seen.add(previous)
        ledger = json.loads((previous / 'spend.json').read_text())
        manifest = json.loads((previous / 'manifest.json').read_text())
        prior += Decimal(ledger['chargedUpperUsd']) + Decimal(str(manifest['infrastructureReserveUsd']))
    model_limit = Decimal('4') - prior
    if model_limit <= 0:
        parser.error('Prior suites and infrastructure reserves exhaust the approved total')
    # Refuse existing evidence rather than accidentally repeating paid tests.
    folder.mkdir(parents=True, exist_ok=False)
    save(folder / 'manifest.json', {'model': 'gpt-5-mini', 'modelLimitUsd': str(model_limit),
         'priorReservedUsd': str(prior), 'totalAuthorizationUsd': 5,
         'priorOutputs': [str(path.resolve()) for path in args.prior_output],
         'infrastructureReserveUsd': 1, 'cases': CASES,
         'scope': 'Fresh full-pipeline builds on pinned model; not production default-provider comparison.'})
    for case in CASES:
        out = folder / case
        out.mkdir()
        project = str(uuid4())
        save(out / 'identity.json', {'projectId': project})
        print('Starting', case, flush=True)
        with (out / 'raw.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen([sys.executable, '-X', 'utf8', '-u', '-m',
                'benchmarks.fresh', '--output', str(folder), '--worker', case],
                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                process.wait(timeout=18 * 60)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                save(out / 'timeout.json', {'seconds': 1080})
        # Retry cleanup after worker crashes, before another sandbox is started.
        try:
            cleanup(out, project)
        except Exception as error:
            save(out / 'cleanup-error.json', {'type': type(error).__name__})
            raise RuntimeError('Cleanup must succeed before continuing') from error
        print('Finished', case, 'exit', process.returncode, flush=True)


if __name__ == '__main__':
    main()
