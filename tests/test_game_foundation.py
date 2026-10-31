import json,time
from types import SimpleNamespace
import pytest
from agent.game_foundation import survival_foundation_fits, validate_survival_design
from agent.parallel_build import draft_project


def design():
    return {'title':'Ashline Survival','brand':['ASH','LINE'],'subtitle':'Survival protocol',
        'eyebrow':'The perimeter is falling','headline':['HOLD','THE','LINE.'],
        'description':'Move, build your edge and survive the outbreak.','operation':'Operation Ashline',
        'enemySignal':'Hostiles approaching','storageKey':'ashline-survival',
        'colors':{'accent':'#d3e6ab','background':'#080d0d','text':'#e6eadc','player':'#4f6866','enemy':'#56634a',
                  'ground':['#182320','#25251e','#1b252b','#1b1d29','#29221f']},
        'balance':{'dashCooldown':4.5,'pulseCooldown':12},
        'levels':[{'id':i+1,'name':name,'tag':'Hold the perimeter','brief':'Clear the waves and secure the next sector.',
                   'color':'#a7d4bd','waves':waves,'speed':speed,'layout':i} for i,(name,waves,speed) in enumerate([
                       ('Courtyard',[4,6],45),('Loading Bay',[6,8],52),('Depot',[8,10],64),('Blackout',[10,12],70),('Extraction',[12,15],78)])]}


def test_foundation_is_selected_only_for_compatible_new_game_requests():
    assert survival_foundation_fits('Build a zombie wave survival game',{'productType':'game'})
    for request in ['Zombie tower defense','Zombie turn based game','Zombie idle game','Zombie first person shooter','Zombie puzzle','Zombie wave multiplayer','Zombie wave shooter with three levels','Zombie wave without skills']:
        assert not survival_foundation_fits(request,{'productType':'game'})
    assert survival_foundation_fits('Build a game with zombies and shooting',{'productType':'game'})
    assert not survival_foundation_fits('Zombie wave game',{'productType':'app'})


def test_agent_authors_the_design_while_reusing_actual_tested_runtime_and_interface():
    calls=[]
    def generate(messages,*_,**kwargs):
        assert kwargs['response_schema']['properties']['gameDesign']['required']
        calls.append(messages)
        return SimpleNamespace(text=json.dumps({'gameDesign':design(),'designDecision':'A readable quarantine-zone composition'}))
    files=draft_project('Build a zombie wave survival game',json.dumps({'designBrief':{'productType':'game'},'files':{}}),lambda _:SimpleNamespace(generate=generate),time.monotonic()+420)
    assert len(calls)==1
    assert json.loads(files['src/gameDesign.js'].removeprefix('export const GAME_DESIGN = ').rstrip(';\n'))==design()
    assert 'GAME_DESIGN.levels' in files['src/projectLogic.js']
    assert 'GAME_DESIGN.headline[0]' in files['src/App.jsx']
    assert '.movement-pad' in files['src/styles.css']
    assert 'import "./styles.css"' in files['src/main.jsx']
    assert 'foundations.css' not in files['src/main.jsx'] and 'design-tokens.css' not in files['src/main.jsx']
    assert 'usePersistentState' in files['src/App.jsx']
    assert 'browser playtests' in files['.genesys-game-plan.json']


def test_invalid_balance_or_asset_injection_is_rejected_instead_of_silently_installing():
    assert validate_survival_design(design())
    for mutate in [lambda d:d['balance'].update(pulseCooldown=0),lambda d:d['colors'].update(background='url(https://invalid.test/x)'),lambda d:d['levels'][0].update(waves=[10000,10000])]:
        value=design();mutate(value)
        with pytest.raises(ValueError):validate_survival_design(value)


def test_new_foundation_contract_is_grounded_and_unsupported_additions_keep_the_normal_planner():
    from agent.build_spec import prepare_build_spec
    from agent.game_playtests import supports_contract
    class Workspace:
        def __init__(self):self.files={'src/App.jsx':'Your project is ready'}
        def read_file(self,path):return {'content':self.files.get(path,'')}
        def write_file(self,path,value):self.files[path]=value;return {'status':'success'}
    def forbidden(*_):raise AssertionError('Known foundation requirements do not need invented ammo/DOM/RTS contracts')
    spec=prepare_build_spec(Workspace(),'Build a polished zombie wave survival game',{'productType':'game','buildIntent':'new-product'},SimpleNamespace(generate=forbidden))
    assert supports_contract(spec)
    assert 'ammo' not in json.dumps(spec).casefold() and 'resource rail' not in json.dumps(spec).casefold()
    assert len([r for r in spec['requirements'] if r['scope']=='browser'])==10
    extended=dict(spec,requirements=spec['requirements']+[{'id':'custom-boss','name':'Boss fight','scope':'browser','acceptance':'Defeat the requested boss'}])
    assert not supports_contract(extended)
    assert not survival_foundation_fits('Zombie wave survival with a boss and inventory',{'productType':'game'})


class EditedGame:
    def __init__(self, spec):
        self.files = {'src/App.jsx': 'export default function App(){return <main>Zombies</main>}', '.genesys-build-spec.json': json.dumps(spec)}
    def read_file(self, path):
        return {'content': self.files.get(path, '')}
    def write_file(self, path, content):
        self.files[path] = content
        return {'status': 'success'}
    def list_files(self, *_):
        return {'files': [{'path': 'src/App.jsx'}]}


def edit_provider():
    answer = {'pages': ['Game'], 'requirements': [{'id': 'r1', 'name': 'Faster zombies', 'scope': 'browser', 'acceptance': 'After pressing Start game zombies reach the player sooner.'}], 'assetRules': [], 'designIntent': 'Same game'}
    return SimpleNamespace(generate=lambda *_: SimpleNamespace(text=json.dumps(answer)))


def test_small_game_edit_keeps_the_trusted_tests_and_adds_a_check_for_the_change():
    from agent.build_spec import prepare_build_spec
    from agent.game_playtests import foundation_contract, supports_contract
    game = EditedGame(foundation_contract('Create a zombie game'))
    spec = prepare_build_spec(game, 'make the zombies faster', {'productType': 'game', 'buildIntent': 'edit-product'}, edit_provider())
    assert supports_contract(spec)
    assert [r['id'] for r in spec['editRequirements']] == ['edit-r1']
    assert json.loads(game.files['.genesys-build-spec.json'])['requestHash'] == spec['requestHash']


@pytest.mark.parametrize('prompt', ['give the player 10 health', 'remove the dash skill', 'make it three levels', 'rename the Start game button'])
def test_edit_that_changes_what_the_tests_assert_does_not_keep_them(prompt):
    from agent.build_spec import keeps_foundation_tests
    from agent.game_playtests import foundation_contract
    assert not keeps_foundation_tests(foundation_contract('Create a zombie game'), prompt, {'buildIntent': 'edit-product'})


def test_only_a_foundation_game_edit_keeps_the_tests():
    from agent.build_spec import keeps_foundation_tests
    from agent.game_playtests import foundation_contract
    assert not keeps_foundation_tests({'requirements': [{'id': 'r1'}]}, 'make the zombies faster', {'buildIntent': 'edit-product'})
    assert not keeps_foundation_tests(foundation_contract('x'), 'make the zombies faster', {'buildIntent': 'new-product'})


def test_recheck_of_an_edit_keeps_the_check_written_for_that_edit():
    from agent.build_spec import prepare_build_spec
    from agent.game_playtests import foundation_contract
    brief = {'productType': 'game', 'buildIntent': 'edit-product'}
    game = EditedGame(foundation_contract('Create a zombie game'))
    first = prepare_build_spec(game, 'make the zombies faster', brief, edit_provider())
    again = prepare_build_spec(game, 'make the zombies faster', brief, None, restore_foundation=True)
    assert again['editRequirements'] == first['editRequirements']


def test_edit_check_failures_and_gaps_are_reported_on_the_build():
    from agent.game_playtests import add_edit_checks
    edits = [{'id': 'edit-r1'}, {'id': 'edit-r2'}]
    base = lambda: {'status': 'success', 'issues': [], 'unverifiedCore': [], 'testedInteractions': ['Regression'],
                    'coverage': {'requirements': [{'id': 'r1'}], 'passedIds': ['r1']}}
    result = add_edit_checks(base(), {'issues': [], 'testedInteractions': ['Faster'], 'coverage': {'passedIds': ['edit-r1']}, '_verifiedPlan': {}}, edits)
    assert result['status'] == 'success' and result['coverage']['passedIds'] == ['r1', 'edit-r1']
    assert result['unverifiedCore'] == ['edit-r2: Edit check did not complete']
    result = add_edit_checks(base(), {'issues': ['Zombies did not speed up'], 'coverage': {}}, edits[:1])
    assert result['status'] == 'error' and result['issues'] == ['Zombies did not speed up']
