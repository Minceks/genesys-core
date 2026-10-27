import json
from types import SimpleNamespace
import pytest
from agent.build_spec import validate_regression_evidence,regression_schema,prepare_build_spec

SOURCE='const [view,setView]=useState("start"); <button onClick={()=>setView("play")}>Play</button>'

def requirement(acceptance):return {'id':'R1','name':'Regression','scope':'browser','acceptance':acceptance}

@pytest.mark.parametrize('acceptance',['Expose a HUD scale preference control in Settings.', 'Reset Progress clears saved levels.', 'Each named view has a unique URL/hash and can be opened directly.'])
def test_nonquoted_inventions_are_rejected(acceptance):
    with pytest.raises(ValueError,match='unsupported new'):
        validate_regression_evidence({'requirements':[requirement(acceptance)]},{'src/App.jsx':SOURCE},'Improve game UI')

def test_explicit_feature_requests_are_preserved():
    spec={'requirements':[requirement('Expose HUD scale in Settings.')]}
    assert validate_regression_evidence(spec,{'src/App.jsx':SOURCE},'Add HUD scale to Settings')==spec

def test_evidence_must_be_a_real_exact_source_excerpt():
    spec={'requirements':[requirement('Start gameplay with Play.')]}
    with pytest.raises(ValueError,match='needs sourceEvidence'):
        validate_regression_evidence(spec,{'src/App.jsx':SOURCE},'Improve UI',True)
    spec['requirements'][0]['sourceEvidence']={'path':'src/App.jsx','excerpt':'const inventedHudScale = useState("large")'}
    with pytest.raises(ValueError,match='exact characters'):
        validate_regression_evidence(spec,{'src/App.jsx':SOURCE},'Improve UI',True)
    spec['requirements'][0]['sourceEvidence']={'path':'src/App.jsx','excerpt':SOURCE}
    assert validate_regression_evidence(spec,{'src/App.jsx':SOURCE},'Improve UI',True)==spec

def test_structured_visual_edit_retries_ungrounded_contract_before_saving():
    calls=[];saved=[]
    class Workspace:
        def read_file(self,path):return {'content':SOURCE if path=='src/App.jsx' else '{}'}
        def write_file(self,path,content):saved.append(json.loads(content));return {'status':'success'}
    def generate(messages,schema):
        calls.append(messages)
        assert 'sourceEvidence' in schema['properties']['requirements']['items']['required']
        assert not saved
        spec={'pages':['Home'],'requirements':[requirement('Start gameplay with Play.')],'assetRules':[],'designIntent':'Readable game UI'}
        if len(calls)>1:spec['requirements'][0]['sourceEvidence']={'path':'src/App.jsx','excerpt':SOURCE}
        return SimpleNamespace(text=json.dumps(spec))
    result=prepare_build_spec(Workspace(),'Improve game UI',{'buildIntent':'edit-product'},SimpleNamespace(generate_structured=generate))
    assert len(calls)==2 and len(saved)==1
    assert result['requirements'][0]['sourceEvidence']['excerpt']==SOURCE

def test_grounded_edit_schema_stays_within_provider_limits():
    from agent.structured_schema import validate_schema_limits
    validate_schema_limits(regression_schema())


def test_focused_edit_cannot_bypass_policy_migration():
    from agent.build_spec import validate_current_spec,PLANNING_POLICY_VERSION
    spec={'pages':['Home'],'requirements':[requirement('Start gameplay with Play.')], 'planningPolicyVersion':5}
    with pytest.raises(ValueError,match='older planning policy'):validate_current_spec(spec)
    spec['planningPolicyVersion']=PLANNING_POLICY_VERSION
    assert validate_current_spec(spec)==spec
