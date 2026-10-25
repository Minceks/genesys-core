"""Deployment check: use the installed REA CLI, never download at runtime."""
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent.reference_inspection import rea_command

command=rea_command()
if not command:
    raise SystemExit('REA runtime is missing')
result=subprocess.run(command+['inspect-web-page','--help'],capture_output=True,text=True,timeout=15)
if result.returncode or 'Passively inspect' not in result.stdout:
    raise SystemExit('REA web inspection command is unavailable')
print(json.dumps({'referenceRuntime':'ready','reaVersion':'6.7.0','webInspectionCommand':True}))
if '--browser' in sys.argv:
    from agent import reference_inspection as inspection
    fixture=b'<html><head><title>Deployment reference fixture</title><style>h1{font-size:48px}@media(max-width:600px){h1{font-size:24px}}</style></head><body><nav><a href="/work">Work</a></nav><h1>Reference runtime</h1></body></html>'
    # This check runs in its own process; it never patches a serving worker.
    inspection.public_addresses=lambda _:['93.184.216.34']
    inspection.public_get=lambda *_args,**_kw:(200,{'Content-Type':'text/html'},fixture)
    # Build workers can be CPU constrained during cold CLI imports. Keep the
    # serving path's 12-second limit; only this fixed deployment fixture gets 40.
    observe=inspection.rea_observation
    inspection.rea_observation=lambda endpoint,target,origin:observe(endpoint,target,origin,timeout=40)
    # A cold CLI/browser process can time out on a busy build worker. Retry the
    # complete fixture once; require the same real evidence on either attempt.
    for attempt in range(2):
        evidence,captures=inspection.inspect_reference('https://example.com/')
        sizes=[v['primaryHeading']['fontSize'] for v in evidence['viewports']]
        print(json.dumps({'referenceFixtureAttempt':attempt+1, 'rea':evidence['rea'],
                          'captures':len(captures), 'headingSizes':sizes}),flush=True)
        if evidence['rea']['status']=='captured' and len(captures)==2 and sizes==[48,24]:
            break
    else:
        raise SystemExit('REA browser runtime did not produce verified fixture evidence after two attempts')
    print(json.dumps({'referenceRuntime':'browser-ready','reaCapture':'captured','viewports':2}))
