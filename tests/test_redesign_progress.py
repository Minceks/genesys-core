import pytest
from agent.design_strategy import requests_redesign
from agent.redesign_verification import presentation_changed


@pytest.mark.parametrize('prompt',['make the game with better UI designe','Improve the UI','Make the UI better','A more modern design','Redesign the dashboard'])
def test_visual_quality_requests_select_redesign_behavior(prompt):assert requests_redesign(prompt)


@pytest.mark.parametrize('prompt',['Fix email validation','Change the favicon','Add quantity controls','Make the game faster','Improve checkout validation'])
def test_functional_or_small_asset_changes_do_not_trigger_redesign(prompt):assert not requests_redesign(prompt)


def diff(path,before,after):
    return f'diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n'+'\n'.join('-'+line for line in before.splitlines())+'\n'+'\n'.join('+'+line for line in after.splitlines())


def test_title_favicon_and_planning_changes_cannot_be_claimed_as_redesign():
    before='<html><head><title>Old</title><link rel="icon" href="old.svg"></head><body><div id="root"></div><script src="/src/main.jsx"></script></body></html>'
    after=before.replace('Old','New').replace('old.svg','new.svg')
    changes=diff('index.html',before,after)+'\n'+diff('public/favicon.svg','<svg/>','<svg><path/></svg>')+'\n'+diff('.genesys-design.json','{}','{"redesign":true}')
    assert not presentation_changed(changes)
    assert not presentation_changed(diff('src/styles.css','body{color:red}','/* Updated theme */\nbody{color:red}'))


@pytest.mark.parametrize('path,before,after',[
    ('src/styles.css','body{display:block}','body{display:grid}'),
    ('src/App.jsx','<main>Old</main>','<main className="hero">New</main>'),
    ('app/page.tsx','<main/>','<main><header>New view</header></main>'),
    ('index.html','<html><body>Old view</body></html>','<html><body>New view</body></html>'),
    ('index.html','<head><style>body{color:red}</style></head>','<head><style>body{color:blue}</style></head>'),
    ('src/scene.js','ctx.fillStyle="white"','ctx.fillStyle="black"'),
    ('index.html','<script>ctx.fillStyle="white"</script>','<script>ctx.fillStyle="black"</script>'),
])
def test_actual_presentation_changes_are_eligible_for_visual_review(path,before,after):
    assert presentation_changed(diff(path,before,after))


def test_new_components_and_canvas_scripts_are_not_lost_with_untracked_git_files():
    assert presentation_changed('',{'src/Scene.svelte':'<main><h1>New scene</h1></main>'})
    assert presentation_changed('',{'scene.js':"document.body.append(document.createElement('main'))"})
    assert not presentation_changed('',{'public/favicon.svg':'<svg><path/></svg>','.genesys-design.json':'{"redesign":true}'})
