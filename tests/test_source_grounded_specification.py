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
        assert 'sourceEvidence' in schema['properties']['requirements']['items']['anyOf'][0]['required']
        assert not saved
        spec={'pages':['Home'],'requirements':[requirement('Start gameplay with Play.')],'assetRules':[],'designIntent':'Readable game UI'}
        if len(calls)>1:spec['requirements'][0]['sourceEvidence']={'referenceId':'E001'}
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


def test_catalog_resolves_original_source_without_model_transcription():
    from agent.spec_evidence import evidence_catalog,resolve_evidence
    source='const labels = "Touch controls";\r\n'+'// unicode: caf? ? ??\n'*100
    catalog=evidence_catalog({'src/App.jsx':source})
    assert len(catalog)>1
    spec={'requirements':[dict(requirement('Preserve controls.'),sourceEvidence={'referenceId':'E001'})]}
    resolve_evidence(spec,catalog)
    evidence=spec['requirements'][0]['sourceEvidence']
    assert evidence['excerpt']==source[:1000]
    validate_regression_evidence(spec,{'src/App.jsx':source},'Improve UI',True)
    spec['requirements'][0]['sourceEvidence']={'referenceId':'FAKE'}
    with pytest.raises(ValueError,match='existing sourceEvidence'):resolve_evidence(spec,catalog)


def test_reference_schema_restricts_ids_and_omits_transcription_fields():
    schema=regression_schema(['E001','E002'])
    items=schema['properties']['requirements']['items']['anyOf']
    assert items[0]['properties']['scope']['enum']==['browser']
    assert items[1]['properties']['sourceEvidence']=={'type':'null'}
    evidence=items[0]['properties']['sourceEvidence']
    assert evidence['required']==['referenceId']
    assert evidence['properties']['referenceId']['enum']==['E001','E002']
    from agent.structured_schema import validate_schema_limits
    validate_schema_limits(schema)


def test_planning_context_uses_catalog_without_duplicate_full_source():
    class Workspace:
        def read_file(self,path):return {'content':SOURCE if path=='src/App.jsx' else '{}'}
        def write_file(self,*_):return {'status':'success'}
    def generate(messages,schema):
        context=json.loads(messages[1]['content'])
        assert 'implementationSources' not in context and 'existingImplementation' not in context
        assert context['sourceEvidenceOptions']==[{'referenceId':'E001','path':'src/App.jsx','excerpt':SOURCE}]
        spec={'pages':['Home'],'requirements':[dict(requirement('Play opens the game.'),sourceEvidence={'referenceId':'E001'})],'assetRules':[],'designIntent':'Readable UI'}
        return SimpleNamespace(text=json.dumps(spec))
    result=prepare_build_spec(Workspace(),'Improve UI',{'buildIntent':'edit-product'},SimpleNamespace(generate_structured=generate))
    assert result['requirements'][0]['sourceEvidence']=={'referenceId':'E001','path':'src/App.jsx','excerpt':SOURCE}
