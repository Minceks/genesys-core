import base64
import json
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright

from agent.design_execution import design_execution
from agent.design_quality import BUILD_STANDARD, FAMILY_FINISH
from agent.visual_capture import capture_design_sheet
from agent.visual_review import review_screenshots


@pytest.mark.parametrize('family', list(FAMILY_FINISH))
def test_generation_and_review_share_purpose_specific_criteria(family):
    brief = {'productType': 'app', 'experienceBlueprint': {'family': family}}
    contract = design_execution(brief)['qualityContract']
    calls = []
    def review(instruction, context, images, schema):
        calls.append(context)
        return SimpleNamespace(text=json.dumps({'assessment': 'ready', 'summary': 'Captured views reviewed.', 'findings': []}))
    review_screenshots(SimpleNamespace(review_images=review), brief,
                       [('generated-desktop', b'fixture'), ('generated-phone', b'fixture')])
    assert calls[0]['qualityContract'] == contract
    assert contract['family'] == family
    assert contract['deliveryStandard'] == BUILD_STANDARD
    assert contract['productFinish'] == FAMILY_FINISH[family][1]
    assert 'scope' in contract and len(contract['criteria']) == 6
    if family != 'commerce':
        assert contract['focus'] != FAMILY_FINISH['commerce'][0]


def test_new_briefs_receive_quality_contract_and_edits_keep_identity(monkeypatch):
    from tests.test_visual_system import Workspace, prepare
    workspace = Workspace()
    original = prepare(monkeypatch, workspace, 'Build a documentation website for our SDK')
    assert original['designExecution']['qualityContract']['family'] == 'documentation'
    edited = prepare(monkeypatch, workspace, 'Fix the contact button')
    assert edited['designExecution']['qualityContract'] == original['designExecution']['qualityContract']
    assert edited['visualSystem'] == original['visualSystem']


def test_actual_build_planning_receives_shared_design_contract():
    from agent.build_spec import prepare_build_spec
    brief = {'productType': 'dashboard', 'buildIntent': 'new-product'}
    brief['designExecution'] = design_execution(brief)
    calls = []
    class Workspace:
        def read_file(self, _): return {'content': '{}'}
        def write_file(self, *args): return {'status': 'success'}
    def generate(messages, _):
        calls.append(json.loads(messages[-1]['content']))
        return SimpleNamespace(text=json.dumps({'pages': ['Overview'], 'designIntent': 'Analytical hierarchy',
            'assetRules': [], 'requirements': [{'id': 'B1', 'name': 'Date filter', 'scope': 'browser',
            'acceptance': 'Select a date range and verify the visible records and summary update.'}]}))
    prepare_build_spec(Workspace(), 'Build a dashboard', brief, SimpleNamespace(generate=generate))
    assert calls[0]['designExecution']['qualityContract'] == brief['designExecution']['qualityContract']


def test_real_contact_sheet_contains_supporting_content_and_preserves_browser_state():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={'width': 1280, 'height': 800})
            page.set_content('''<style>body{margin:0}section{height:800px}</style>
                <section style="background:#c83030">Hero</section>
                <section style="background:#3040c8">Supporting work</section>
                <section style="background:#30a040">Case study</section>
                <section>Footer</section>''')
            page.evaluate('scrollTo(0,350)')
            sheet, samples = capture_design_sheet(page)
            assert len(samples) == 3 and samples[0]['scrollY'] == 0
            assert samples[1]['scrollY'] >= 800 and samples[2]['scrollY'] >= 1600
            assert page.evaluate('scrollY') == 350
            assert page.viewport_size == {'width': 1280, 'height': 800}
            assert len(page.context.pages) == 1
            assert len(sheet) <= 2_000_000
            # Decode the real JPEG in-browser and inspect all three panel pixels.
            encoded = base64.b64encode(sheet).decode('ascii')
            pixels = page.evaluate('''async (data) => {
                const img=new Image();img.src='data:image/jpeg;base64,'+data;await img.decode();
                const canvas=document.createElement('canvas');canvas.width=img.width;canvas.height=img.height;
                const ctx=canvas.getContext('2d');ctx.drawImage(img,0,0);
                return [100,924,1748].map(y=>[...ctx.getImageData(600,y,1,1).data]);
            }''', encoded)
            assert pixels[0][0] > pixels[0][2] * 2  # red hero
            assert pixels[1][2] > pixels[1][0] * 2  # blue supporting work
            assert pixels[2][1] > pixels[2][0] * 2  # green case study
        finally:
            browser.close()


def test_failed_capture_restores_scroll_without_leaving_pages_open(monkeypatch):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            page.set_content('<main style="height:3000px">A working app</main>')
            page.evaluate('scrollTo(0,210)')
            def fail(**kwargs): raise RuntimeError('Screenshot interrupted')
            monkeypatch.setattr(page, 'screenshot', fail)
            with pytest.raises(RuntimeError, match='interrupted'):
                capture_design_sheet(page)
            assert page.evaluate('scrollY') == 210
            assert len(page.context.pages) == 1
        finally:
            browser.close()


def test_review_records_sample_coverage_without_claiming_unseen_routes():
    details = {'generated-desktop': [{'scrollY': 0}, {'scrollY': 800}]}
    provider = SimpleNamespace(review_images=lambda instruction, context, images, schema:
        SimpleNamespace(text=json.dumps({'assessment': 'needs_polish', 'summary': 'Body content needs hierarchy.',
            'findings': [{'screenshot': 'generated-desktop', 'area': 'Supporting content at y=800',
                'evidence': 'The service story repeats default cards without a focal point.',
                'correction': 'Use a service-led composition and clearer heading hierarchy.', 'severity': 'major'}]})))
    result = review_screenshots(provider, {'productType': 'website'},
        [('generated-desktop', b'fixture'), ('generated-phone', b'fixture')], capture_details=details)
    assert result['status'] == 'needs_polish'
    assert result['capturedViews'] == details
    assert len(result['screenshots']) == 2


def test_focused_edit_upholds_delivery_standard_without_expanding_scope():
    from agent.edit_scope import guidance
    instructions = guidance('Change the header font size')
    assert BUILD_STANDARD in instructions
    assert 'whole-file replacement and new files are unavailable' in instructions
    assert 'Preserve routes, state, persistence' in instructions
    assert guidance('Build a dashboard') == ''


def test_parallel_planner_both_workers_and_reviewer_receive_delivery_standard(monkeypatch):
    import time
    from agent.parallel_build import draft_project
    calls = []
    def generate(messages, tools):
        instruction = messages[0]['content']
        assert instruction.startswith(BUILD_STANDARD)
        calls.append(instruction)
        if 'Plan a React user application.' in instruction:
            value = {'interface': 'useProjectLogic', 'requirements': ['Complete task creation'],
                     'pageComposition': ['Task workspace']}
        elif 'Review the complete React UI and logic draft' in instruction:
            value = {'valid': True, 'issues': [], 'files': {}}
        elif 'Required files: src/App.jsx' in instruction:
            value = {'files': {'src/App.jsx': 'export default function App(){return <main>Tasks</main>}'}}
        elif 'Required files: src/styles.css' in instruction:
            value = {'files': {'src/styles.css': 'main {max-width:60rem;margin:auto} '}}
        else:
            value = {'files': {'src/projectLogic.js': 'export function useProjectLogic(){return {tasks:[]}}'}}
        return SimpleNamespace(text=json.dumps(value))
    monkeypatch.setenv('GENESYS_PARALLEL_LOGIC_PROVIDER', 'openai')
    files = draft_project('Build a task app', '{}', lambda _: SimpleNamespace(generate=generate), time.monotonic() + 120)
    assert len(calls) == 5
    assert set(files) == {'src/App.jsx', 'src/styles.css', 'src/projectLogic.js'}
