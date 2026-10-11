"""Bound text context and omit binary assets from model conversation text."""
import json
import os
import re
from functools import lru_cache

_BINARY = re.compile(r"data:image/[^;\s]+;base64,[A-Za-z0-9+/=]+|(?<![A-Za-z0-9])[0-9a-fA-F]{2048,}(?![A-Za-z0-9])")


def text_safe(value):
    if isinstance(value, dict):
        return {key: ('[binary asset omitted; use screenshot metadata]' if key.lower() in
                {'image', 'base64', 'imagebase64', 'imagedata', 'screenshotbase64'} else text_safe(item))
                for key, item in value.items()}
    if isinstance(value, list):
        return [text_safe(item) for item in value]
    if isinstance(value, str):
        return _BINARY.sub('[binary asset omitted]', value)
    return value


@lru_cache(maxsize=1)
def encoding():
    import tiktoken
    return tiktoken.get_encoding('o200k_base')


def bounded_messages(messages, tools, limit=None):
    # Token estimates include schemas and envelope overhead. Provider tokenizers
    # differ; retain a conservative margin rather than claiming billing accuracy.
    cap = min(48000, max(2000, int(os.getenv('GENESYS_INPUT_TOKEN_LIMIT', '24000'))))
    if limit is not None:
        cap = min(cap, limit)
    enc = encoding()
    def count(value):
        return len(enc.encode(json.dumps(value, ensure_ascii=False, default=str), disallowed_special=()))
    safe = text_safe(messages)
    allowance = cap - count(tools) - 512
    if allowance < 512:
        raise ValueError('Tool schemas exceed the configured model input budget.')
    if count(safe) <= allowance:
        return safe
    # Convert executed tool history to text to avoid orphaned function-call IDs.
    flat = []
    for message in safe:
        role = message.get('role')
        content = message.get('content') or ''
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, default=str)
        if role == 'tool':
            role = 'user'
            content = 'Already executed tool result:\n' + content
        if role not in {'system', 'user', 'assistant'}:
            continue
        flat.append({'role': role, 'content': content})
    first_user = next((index for index, msg in enumerate(flat) if msg['role'] == 'user'), None)
    priority = list(dict.fromkeys([0] + ([first_user] if first_user is not None else []) + list(range(len(flat)-1, -1, -1))))
    kept = {}
    for index in priority:
        if index >= len(flat):
            continue
        item = flat[index]
        ids = enc.encode(item['content'], disallowed_special=())
        item_cap = min(3000, allowance // 3) if index == 0 else min(2000, allowance // 4) if index == first_user else 6000
        per_item = min(item_cap, allowance - count(list(kept.values())) - 64)
        if per_item < 128:
            break
        if len(ids) > per_item:
            item = dict(item, content=enc.decode(ids[:per_item-40]) + '\n[Context shortened. Read the current file before changing omitted source.]')
        kept[index] = item
    result = [kept[index] for index in sorted(kept)]
    if count(result) > allowance:
        raise ValueError('Unable to fit context into the configured input budget.')
    return result
