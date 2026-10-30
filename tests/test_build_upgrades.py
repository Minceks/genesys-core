import base64
import json
import re
import struct
import time
import zlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent.ai_provider import OpenAIProvider
from agent.build_context import initial_source_context
from agent.image_generation import generate, placeholder, planned_images, produce_image
from agent.parallel_build import draft_project
from agent.progress import model_request_scope, repair_model_scope
from agent.project_starter import STARTER_FILES

PNG = b'\x89PNG\r\n\x1a\nimage'


def image_client(side_effect=None):
    response = SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(PNG).decode())],
                               usage=SimpleNamespace(total_tokens=5000))
    return SimpleNamespace(images=SimpleNamespace(generate=Mock(return_value=response, side_effect=side_effect)))


@pytest.fixture
def budget(monkeypatch):
    monkeypatch.setattr('agent.image_generation.reserve_model_budget', lambda _: {'day': 1})
    monkeypatch.setattr('agent.image_generation.reconcile_model_budget', lambda *_: None)
    monkeypatch.setattr('agent.user_allowance.record', lambda _: None)


def test_image_requests_are_bounded_and_cannot_write_outside_public_images(monkeypatch):
    monkeypatch.setenv('GENESYS_IMAGE_LIMIT', '2')
    good = {'path': 'public/images/hero.png', 'prompt': 'A bright clinic', 'alt': 'Clinic', 'size': '999x999'}
    plan = {'generatedImages': [good, dict(good), {**good, 'path': '../secret.png'}, {**good, 'path': 'src/App.jsx'},
        {**good, 'path': 'public/images/a.png', 'prompt': ''}, {**good, 'path': 'public/images/b.png', 'alt': None}, 'x',
        {**good, 'path': 'public/images/c.png'}, {**good, 'path': 'public/images/d.png'}]}
    images = planned_images(plan)
    assert [item['path'] for item in images] == ['public/images/hero.png', 'public/images/c.png']
    assert images[0]['size'] == '1536x1024'


def test_generation_uses_the_current_model_and_a_bounded_request(budget):
    client = image_client()
    image = {'path': 'public/images/hero.png', 'prompt': 'A clinic', 'size': '1536x1024', 'alt': 'Clinic'}
    with model_request_scope(time.monotonic() + 30):
        assert generate(client, image) == PNG
    kwargs = client.images.generate.call_args.kwargs
    assert kwargs['model'] == 'gpt-image-2.5-flare' and kwargs['timeout'] <= 30
    assert 'No text' in kwargs['prompt'] and kwargs['prompt'].endswith('A clinic')


def test_a_failed_image_saves_a_valid_placeholder_and_never_raises(budget):
    saved = {}
    image = {'path': 'public/images/hero.png', 'prompt': 'A clinic', 'size': '1536x1024', 'alt': 'Clinic'}
    produce_image(image_client(RuntimeError('Provider rejected the request')), image, saved.__setitem__)
    data = saved['public/images/hero.png']
    assert data == placeholder() and data.startswith(b'\x89PNG')
    width, height = struct.unpack('>II', data[16:24])
    assert (width, height) == (1, 1)
    assert len(zlib.decompress(data[41:data.index(b'IEND') - 8])) == 4
    produce_image(image_client(), image, Mock(side_effect=OSError('Sandbox unavailable')))


def test_budget_refusal_falls_back_without_calling_the_provider(monkeypatch):
    def refuse(_):raise RuntimeError('Daily model allowance reached')
    monkeypatch.setattr('agent.image_generation.reserve_model_budget', refuse)
    client, saved = image_client(), {}
    produce_image(client, {'path': 'public/images/a.png', 'prompt': 'x', 'size': '1024x1024', 'alt': 'x'}, saved.__setitem__)
    client.images.generate.assert_not_called()
    assert saved['public/images/a.png'] == placeholder()


class Drafts:
    def __init__(self):
        self.client = image_client()
        self.prompts = []

    def generate(self, messages, tools):
        system = messages[0]['content']
        self.prompts.append(system)
        if 'Plan a React user application' in system:
            return SimpleNamespace(text=json.dumps({'interface': 'useApp()', 'requirements': ['Book'], 'generatedImages': [
                {'path': 'public/images/hero.png', 'prompt': 'A clinic', 'alt': 'Clinic', 'size': '1536x1024'}]}))
        if 'Review the complete React UI' in system:
            return SimpleNamespace(text='{"valid":true,"issues":[],"files":{}}')
        required = re.search(r'Required files: (.*?)\. Optional', system).group(1).split(', ')
        return SimpleNamespace(text=json.dumps({'files': {path: 'export const value = 1\n' for path in required}}))


def test_draft_saves_planned_images_as_assets_not_source(budget):
    provider, saved = Drafts(), {}
    source = json.dumps({'files': {'package.json': STARTER_FILES['package.json']}})
    files = draft_project('Build booking', source, lambda _: provider, 10**12, save_image=saved.__setitem__)
    assert saved == {'public/images/hero.png': PNG}
    assert any('/images/name.png' in prompt for prompt in provider.prompts)
    assert not any(path.startswith('public/') for path in files)


def test_drafts_without_an_asset_writer_never_buy_images():
    provider = Drafts()
    source = json.dumps({'files': {'package.json': STARTER_FILES['package.json']}})
    draft_project('Build booking', source, lambda _: provider, 10**12)
    provider.client.images.generate.assert_not_called()


def provider_with(create):
    return OpenAIProvider(model='gpt-5-mini', client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))


def completion(text='ok'):
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content=text, tool_calls=[]))])


def chunk(text=None, finish=None, usage=None):
    choices = [] if usage else [SimpleNamespace(delta=SimpleNamespace(content=text), finish_reason=finish)]
    return SimpleNamespace(choices=choices, usage=usage)


@pytest.fixture
def quiet_provider(monkeypatch):
    monkeypatch.setattr('agent.ai_provider.bounded_messages', lambda messages, *_, **__: messages)
    monkeypatch.setattr('agent.ai_provider.record_model_usage', lambda _: None)


DRAFT = [{'role': 'system', 'content': 'DEFAULT BUILD STANDARD: draft'}, {'role': 'user', 'content': 'Build'}]


def test_design_requests_stream_and_assemble_a_complete_response(quiet_provider, monkeypatch):
    monkeypatch.setenv('GENESYS_STREAM_DESIGN', '1')
    seen = {}
    monkeypatch.setattr('agent.model_context.reconcile_model_budget', lambda _, tokens: seen.update(tokens=tokens))
    create = Mock(return_value=iter([chunk('{"a"'), chunk(':1}'), chunk(finish='stop'),
                                     chunk(usage=SimpleNamespace(total_tokens=321))]))
    result = provider_with(create).generate(DRAFT, [])
    assert result.text == '{"a":1}'
    kwargs = create.call_args.kwargs
    assert kwargs['stream'] is True and kwargs['stream_options'] == {'include_usage': True}
    assert seen['tokens'] == 321


def test_a_stream_that_outlives_its_budget_is_stopped(quiet_provider, monkeypatch):
    monkeypatch.setenv('GENESYS_STREAM_DESIGN', '1')
    def endless():
        while True:
            time.sleep(.02)
            yield chunk('x')
    with model_request_scope(time.monotonic() + 1.3):
        with pytest.raises(TimeoutError):
            provider_with(Mock(return_value=endless())).generate(DRAFT, [])


def test_tool_requests_never_stream(quiet_provider, monkeypatch):
    monkeypatch.setenv('GENESYS_STREAM_DESIGN', '1')
    create = Mock(return_value=completion())
    tools = [{'function': {'name': 'write_file'}}]
    provider_with(create).generate([{'role': 'user', 'content': 'Edit'}], tools)
    assert 'stream' not in create.call_args.kwargs


def test_repairs_use_the_stronger_model_only_inside_their_scope(quiet_provider, monkeypatch):
    monkeypatch.delenv('GENESYS_REPAIR_MODEL', raising=False)
    create = Mock(return_value=completion())
    tools = [{'function': {'name': 'write_file'}}]
    provider = provider_with(create)
    provider.generate([{'role': 'user', 'content': 'Edit'}], tools)
    assert create.call_args.kwargs['model'] == 'gpt-5-mini'
    with repair_model_scope(True):
        provider.generate([{'role': 'user', 'content': 'Repair'}], tools)
    assert create.call_args.kwargs['model'] == 'gpt-5.4'
    with repair_model_scope(False):
        provider.generate([{'role': 'user', 'content': 'Edit'}], tools)
    assert create.call_args.kwargs['model'] == 'gpt-5-mini'


def test_shared_kit_cannot_crowd_app_source_out_of_repair_context():
    files = [f'src/components/ui/{name}.jsx' for name in ('button', 'card', 'input', 'select')] + ['src/App.jsx', '.genesys-user-project']
    cache = SimpleNamespace(read_file=lambda path: {'status': 'success', 'content': 'source of ' + path})
    context = initial_source_context(cache, files, files[:4])
    assert 'FILE: src/App.jsx' in context and 'components/ui' not in context
