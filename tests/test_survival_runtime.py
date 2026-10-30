import json,runpy,shutil,subprocess
from pathlib import Path
import pytest


def test_reusable_game_runtime_has_real_combat_fair_damage_and_clean_lifecycle(tmp_path):
    node=shutil.which('node')
    if not node:pytest.skip('Node is needed for the shipped game runtime audit')
    root=Path(__file__).resolve().parent.parent
    config=runpy.run_path(str(root/'tests/test_game_foundation.py'))['design']()
    (tmp_path/'package.json').write_text('{"type":"module"}')
    (tmp_path/'gameDesign.js').write_text('export const GAME_DESIGN='+json.dumps(config)+';')
    shutil.copyfile(root/'agent/game_foundations/survival/projectLogic.js',tmp_path/'projectLogic.js')
    result=subprocess.run([node,str(root/'tests/fixtures/survival_engine_audit.mjs'),str(tmp_path/'projectLogic.js')],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    reports=[json.loads(line) for line in result.stdout.splitlines()]
    assert reports[0]['allSectorsCompletable'] and len(reports[0]['checks'])==5
    assert reports[1]['singleSimulation'] and reports[1]['pulseDealsDamage'] and reports[1]['lossAndRetry']
    assert reports[2]['noPerFrameDamage'] and min(reports[2]['fairDamageIntervals'])>=850
