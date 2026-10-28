from agent.engineering_strategy import engineering_strategy
from agent.design_quality import design_quality_contract

def test_requested_game_skills_are_real_mechanics_and_other_products_do_not_inherit_them():
    game=engineering_strategy({'productType':'game','originalRequest':'Zombie survival'},'Polished shooting and skills',{})
    assert len(game['requestedGameMechanics'])==2
    puzzle=engineering_strategy({'productType':'game','originalRequest':'Minimal abstract puzzle'},'Improve puzzle colors',{})
    assert puzzle['requestedGameMechanics']==[]
    app=engineering_strategy({'productType':'app'},'Track employee skills',{})
    assert app['requestedGameMechanics']==[]

def test_game_review_requires_playable_scene_evidence_without_forcing_action_art_on_puzzles():
    contract=design_quality_contract({'productType':'game'})
    assert contract['family']=='game'
    assert 'in-play' in contract['productFinish'] and 'abstract/puzzle' in contract['productFinish']
    assert 'cooldown' in contract['productFinish']
