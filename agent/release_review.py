"""Server-owned release evidence and explicit acknowledgement of its limits."""
import hashlib
import json
import time
from .beta_storage import connection


def _table(db):
    db.execute('''CREATE TABLE IF NOT EXISTS release_reviews(
        project TEXT NOT NULL, checkpoint TEXT NOT NULL, commit_sha TEXT NOT NULL,
        evidence TEXT NOT NULL, updated REAL NOT NULL,
        PRIMARY KEY(project,checkpoint,commit_sha))''')


def save_evidence(project, result):
    checkpoint = result.get('checkpoint') or {}
    if not (result.get('buildPassed') is True and result.get('browserVerified') is True
            and checkpoint.get('status') == 'success' and checkpoint.get('checkpointId') and checkpoint.get('commit')):
        return False
    evidence = {key: result.get(key) for key in ('buildPassed', 'browserVerified', 'buildFingerprint', 'verification')}
    encoded = json.dumps(evidence, ensure_ascii=False)
    if len(encoded.encode()) > 128000:
        raise ValueError('Release evidence exceeds its storage limit')
    with connection() as db:
        _table(db)
        db.execute('INSERT OR REPLACE INTO release_reviews VALUES(?,?,?,?,?)',
                   (project, checkpoint['checkpointId'], checkpoint['commit'], encoded, time.time()))
        db.execute('''DELETE FROM release_reviews WHERE project=? AND rowid NOT IN
            (SELECT rowid FROM release_reviews WHERE project=? ORDER BY updated DESC LIMIT 20)''', (project, project))
    return True


def load_evidence(project, checkpoint, commit):
    with connection() as db:
        _table(db)
        row = db.execute('SELECT evidence FROM release_reviews WHERE project=? AND checkpoint=? AND commit_sha=?',
                         (project, checkpoint, commit)).fetchone()
    return json.loads(row[0]) if row else None


def _list(value):
    return list(dict.fromkeys(item.strip()[:1000] for item in (value if isinstance(value, list) else [])
                             if isinstance(item, str) and item.strip()))[:30]


def review(project, checkpoint, commit):
    evidence = load_evidence(project, checkpoint, commit)
    supplied_report = (evidence or {}).get('verification')
    report = supplied_report if isinstance(supplied_report, dict) else {}
    blockers = _list(report.get('failed')) + _list(report.get('incomplete'))
    if not evidence:
        blockers.append('This version has no saved release evidence. Build and verify it again before publishing; its saved preview is unchanged.')
    elif not (evidence.get('buildPassed') is True and evidence.get('browserVerified') is True):
        blockers.append('Compilation and browser workflow verification must both complete for this version.')
    if evidence and (not isinstance(supplied_report, dict) or not isinstance(report.get('failed'), list)
                     or not isinstance(report.get('incomplete'), list)):
        blockers.append('The verification report is missing or incomplete for this version. Run verification again.')
    visual = report.get('visualReview')
    visual = visual if isinstance(visual, dict) else {}
    visual_status = visual.get('status', 'unreviewed')
    findings = visual.get('findings') if isinstance(visual.get('findings'), list) else []
    # Screenshot findings are judgment, so the owner decides: they appear in the
    # acknowledged review below. Failed or incomplete checks above still block.
    manual = _list(report.get('manualReview'))
    design_notes = ['Open design note: ' + str(finding.get('area') or 'Layout')[:120] + ' — ' + str(finding.get('evidence') or visual.get('summary') or '')[:700]
                    for finding in findings if isinstance(finding, dict) and finding.get('severity') == 'major']
    if visual_status == 'needs_polish' and not design_notes:
        design_notes.append('Open design note: ' + str(visual.get('summary') or 'The screenshot review identified unfinished design.')[:700])
    manual = design_notes + manual
    if visual_status not in {'ready', 'needs_polish'}:
        manual.insert(0, 'Screenshot review is unavailable or was not run. Inspect this version on desktop and phone; no automatic visual approval was obtained.')
    if (visual_status == 'ready' and visual.get('sourceFingerprint') and evidence
            and visual['sourceFingerprint'] != evidence.get('buildFingerprint')):
        visual_status = 'unreviewed'
        manual.insert(0, 'The screenshot review does not match this source version. Review its desktop and phone layouts manually.')
    for finding in findings:
        if isinstance(finding, dict) and finding.get('severity') == 'minor':
            manual.append(str(finding.get('area') or 'Design')[:120] + ': ' + str(finding.get('evidence') or '')[:700])
    deferred = _list(report.get('deferred'))
    limitations = _list(report.get('limitations'))
    acknowledgements = [{'id': 'visual-content', 'label': 'I reviewed this version’s desktop and phone layouts, content and imagery.', 'items': _list(manual)}]
    if deferred:
        acknowledgements.append({'id': 'deferred-integrations',
            'label': 'I understand these integrations remain deferred and are not completed by publishing.', 'items': deferred})
    if limitations:
        acknowledgements.append({'id': 'verification-scope',
            'label': 'I understand the limits of the checks performed on this version.', 'items': limitations})
    value = {'checkpointId': checkpoint, 'commit': commit,
             'status': 'blocked' if blockers else 'needs_review', 'blockers': _list(blockers),
             'visualAssessment': visual_status, 'acknowledgements': acknowledgements}
    digest = hashlib.sha256(json.dumps({'project': project, **value}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {**value, 'reviewHash': digest}


def acknowledged(value, supplied_hash, acknowledgements):
    return (value['status'] != 'blocked' and supplied_hash == value['reviewHash']
            and isinstance(acknowledgements, list)
            and all(isinstance(item, str) for item in acknowledgements)
            and set(acknowledgements) == {item['id'] for item in value['acknowledgements']})
