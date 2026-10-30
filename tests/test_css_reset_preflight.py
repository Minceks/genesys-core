import os
from pathlib import Path
import subprocess
import pytest
from agent.react_preflight import HOOK_PREFLIGHT

@pytest.mark.parametrize('css,rejected',[
    ('.tile{all:unset;display:block;width:100%;padding:12px;border:1px solid #ddd}',True),
    ('.tile{box-sizing:border-box;all:unset;width:100%;padding:12px}',True),
    ('@media(max-width:600px){.tile{all:unset;width:100%;padding:12px}}',True),
    ('.tile{all:unset;box-sizing:border-box;width:100%;padding:12px}',False),
    ('.tile{width:100%;padding:12px}',False),
    ('.tile{all:unset;width:100%;padding:0;border:none}',False),
])
def test_card_reset_cannot_undo_responsive_box_sizing(tmp_path,css,rejected):
    (tmp_path/'src').mkdir();p=tmp_path/'src/styles.css';p.write_text(css)
    root=Path(__file__).resolve().parents[1]
    modules=os.pathsep.join(str(path) for path in (root/'node_modules',root/'.verification-node-deps/node_modules'))
    result=subprocess.run(['node','-e',HOOK_PREFLIGHT],cwd=tmp_path,
        env=dict(os.environ,NODE_PATH=modules),capture_output=True,text=True)
    # The rendered browser is authoritative: another stylesheet can legitimately
    # restore box-sizing, so source evidence alone must never reject the app.
    assert result.returncode==0,result.stderr
    if rejected:assert 'resets box-sizing' in result.stderr
    else:assert 'resets box-sizing' not in result.stderr
    assert p.read_text()==css
