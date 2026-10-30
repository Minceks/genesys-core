import json
import re
from types import SimpleNamespace

import pytest

from agent.build_spec import implementation_sources
from agent.design_foundation import PATH, PLACEHOLDER, prepare_foundation, stylesheet
from agent.parallel_build import DraftReviewFailed, draft_project, normalize_owned_files, planned_files
from agent.project_starter import STARTER_FILES
from agent.ui_kit import FOUNDATION_CSS, STACK_GUIDE, UI_KIT
from agent.visual_system import PALETTES, visual_system


def contrast(first, second):
    def luminance(value):
        channels = [int(value[index:index+2], 16) / 255 for index in (1, 3, 5)]
        r, g, b = [c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4 for c in channels]
        return .2126 * r + .7152 * g + .0722 * b
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + .05) / (low + .05)


def test_starter_ships_the_stack_within_the_sandbox_setup_limit():
    package = json.loads(STARTER_FILES['package.json'])
    for name in ('tailwindcss', '@tailwindcss/vite'):
        assert name in package['devDependencies']
    for name in ('lucide-react', 'motion', 'recharts', 'react-router-dom', 'sonner', 'radix-ui'):
        assert name in package['dependencies']
    # The starter travels as a single process argument, limited to 128 KB on Linux.
    assert len(json.dumps({k: v for k, v in STARTER_FILES.items()})) < 100_000
    assert "@tailwindcss/vite" in STARTER_FILES['vite.config.js'] and "'@':" in STARTER_FILES['vite.config.js']
    assert 'Your project is ready' in STARTER_FILES['src/App.jsx']
    assert '<Toaster' in STARTER_FILES['src/main.jsx']


def test_every_installed_package_used_by_the_kit_is_declared():
    package = json.loads(STARTER_FILES['package.json'])
    declared = set(package['dependencies'])
    for source in UI_KIT.values():
        for name in re.findall(r"from '([^.'][^']*)'", source):
            assert name in declared, name


def test_guide_names_only_kit_files_that_exist():
    listed = re.search(r'Components, imported.*?Use cn\(\)', STACK_GUIDE, re.S).group(0)
    for name in re.findall(r'\b([a-z]+) \(', listed):
        assert f'src/components/ui/{name}.jsx' in UI_KIT, name


def test_project_defaults_cannot_override_utilities():
    # Unlayered CSS beats every Tailwind utility, whatever its specificity.
    system = visual_system('p', 'website', 'x', {'direction': 'modern'})
    css = stylesheet(system, modern=True)
    assert '@layer base' in FOUNDATION_CSS and '@layer base' in css
    assert css.index('@layer base') < css.index(':where(button:not([class]))')
    assert ':where(button){' not in css


def test_older_projects_keep_their_stylesheet_and_never_import_new_packages():
    system = visual_system('p', 'website', 'x', {'direction': 'modern'})
    css = stylesheet(system)
    assert '@import' not in css and '@layer' not in css and ':where(button){' in css


def test_font_imports_follow_the_project_package():
    class Workspace:
        project_id = 'p'
        def __init__(self, package):
            self.files = {'src/main.jsx': "import './design-tokens.css'", PATH: PLACEHOLDER, 'package.json': package}
        def read_file(self, path):return {'content': self.files[path]}
        def write_file(self, path, content):
            self.files[path] = content
            return {'status': 'success'}
    system = visual_system('p', 'website', 'x', {'direction': 'modern'})
    modern = Workspace(STARTER_FILES['package.json'])
    older = Workspace('{"dependencies":{"react":"19"}}')
    prepare_foundation(modern, system)
    prepare_foundation(older, system)
    assert modern.files[PATH].startswith('@import "@fontsource-variable/')
    assert '@import' not in older.files[PATH]


@pytest.mark.parametrize('name', ['indigo', 'emerald', 'ember', 'ocean'])
def test_default_palettes_meet_contrast_targets(name):
    tokens = PALETTES[name]
    assert contrast(tokens['accent'], tokens['accentText']) >= 4.5
    assert contrast(tokens['text'], tokens['surface']) >= 7
    assert contrast(tokens['muted'], tokens['background']) >= 4.5


def test_default_look_varies_and_editorial_keeps_its_serif():
    systems = [visual_system(f'p{i}', 'website', 'x', {'direction': 'modern'}) for i in range(40)]
    assert len({item['palette']['name'] for item in systems}) == 4
    assert len({item['type']['displayFamily'] for item in systems}) == 3
    assert 'Fraunces' in visual_system('p', 'website', 'x', {'direction': 'editorial'})['type']['displayFamily']


def test_planned_files_are_bounded_and_cannot_replace_the_kit():
    plan = {'primaryFiles': [{'path': 'src/pages/Home.jsx'}, 'src/components/Hero.jsx', {'path': './src/hooks/useCart.js'},
        {'path': 'src/components/ui/button.jsx'}, {'path': 'src/lib/utils.js'}, {'path': '../secret.js'},
        {'path': 'src/App.jsx'}, {'path': 'src/pages/Home.jsx'}, {'path': 'src/components/x.css'}, None]}
    assert planned_files(plan, 'primaryFiles') == ['src/pages/Home.jsx', 'src/components/Hero.jsx', 'src/hooks/useCart.js']
    assert planned_files(plan, 'primaryFiles', ['src/pages/Home.jsx'])[0] == 'src/components/Hero.jsx'
    assert len(planned_files({'k': [f'src/pages/P{i}.jsx' for i in range(20)]}, 'k')) == 8
    with pytest.raises(ValueError):
        normalize_owned_files({'src/components/ui/button.jsx': 'x'}, ['src/App.jsx'])


class Drafts:
    def __init__(self, fail=None):
        self.fail, self.prompts = fail, []

    def generate(self, messages, tools):
        system = messages[0]['content']
        self.prompts.append(system)
        if 'Plan a React user application' in system:
            return SimpleNamespace(text=json.dumps({'interface': 'useApp()', 'requirements': ['Book'],
                'primaryFiles': [{'path': 'src/pages/Home.jsx', 'exports': ['Home'], 'purpose': 'Home'}],
                'secondaryFiles': [{'path': 'src/components/Hero.jsx', 'exports': ['Hero'], 'purpose': 'Hero'}]}))
        if 'Review the complete React UI' in system:
            return SimpleNamespace(text='{"valid":true,"issues":[],"files":{}}')
        required = re.search(r'Required files: (.*?)\. Optional', system).group(1).split(', ')
        if self.fail and self.fail in required:
            raise TimeoutError('Synthetic worker timeout')
        return SimpleNamespace(text=json.dumps({'files': {path: 'export const value = 1\n' for path in required}}))


def modern_source():
    return json.dumps({'files': {'package.json': STARTER_FILES['package.json']}})


def test_workers_deliver_a_multi_file_app_on_the_modern_stack():
    provider = Drafts()
    files = draft_project('Build booking', modern_source(), lambda _: provider, 10**12)
    assert {'src/App.jsx', 'src/projectLogic.js', 'src/styles.css', 'src/pages/Home.jsx', 'src/components/Hero.jsx'} == set(files)
    assert all('MODERN STACK' in prompt for prompt in provider.prompts)
    assert not any('plain CSS and React' in prompt for prompt in provider.prompts)


def test_older_sources_keep_the_previous_worker_contract():
    provider = Drafts()
    files = draft_project('Build booking', json.dumps({'files': {}}), lambda _: provider, 10**12)
    assert set(files) == {'src/App.jsx', 'src/projectLogic.js', 'src/styles.css'}
    assert not any('MODERN STACK:' in prompt for prompt in provider.prompts)


def test_a_failed_worker_reports_its_planned_files_for_repair():
    provider = Drafts(fail='src/components/Hero.jsx')
    with pytest.raises(DraftReviewFailed) as caught:
        draft_project('Build booking', modern_source(), lambda _: provider, 10**12)
    assert 'src/components/Hero.jsx' in str(caught.value) and 'src/styles.css' in str(caught.value)
    assert 'src/pages/Home.jsx' in caught.value.drafts


def test_source_review_follows_alias_imports_and_skips_the_shared_kit():
    files = {'src/App.jsx': "import { Home } from '@/pages/Home'\nimport { Button } from '@/components/ui/button'",
             'src/pages/Home.jsx': "import './local'", 'src/pages/local.js': 'export {}',
             'src/components/ui/button.jsx': 'kit'}
    workspace = SimpleNamespace(read_file=lambda path: {'content': files.get(path, '')})
    assert set(implementation_sources(workspace)) == {'src/App.jsx', 'src/pages/Home.jsx', 'src/pages/local.js'}
