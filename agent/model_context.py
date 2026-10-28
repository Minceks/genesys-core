"""Bound text context and omit binary assets from model conversation text."""
import json
import os
import re
import time
from .beta_storage import connection
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


class ModelBudgetExceeded(RuntimeError):
    pass


def reserve_model_budget(tokens):
    configured_limit = int(os.getenv('GENESYS_DAILY_MODEL_TOKEN_BUDGET', '2000000'))
    # An explicit zero disables GeneSys's internal daily block. Provider limits
    # and per-request context/output bounds remain independent.
    if configured_limit == 0:
        return
    limit = max(10000, configured_limit)
    day = int(time.time() // 86400)
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE IF NOT EXISTS model_allowance(day INTEGER PRIMARY KEY, reserved INTEGER NOT NULL)')
        db.execute('DELETE FROM model_allowance WHERE day < ?', (day-7,))
        row = db.execute('SELECT reserved FROM model_allowance WHERE day=?', (day,)).fetchone()
        used = row[0] if row else 0
        if used + tokens > limit:
            raise ModelBudgetExceeded('Daily model allowance reached. Saved project files are preserved; please return after the UTC daily reset.')
        db.execute('INSERT INTO model_allowance VALUES(?,?) ON CONFLICT(day) DO UPDATE SET reserved=excluded.reserved', (day, used+tokens))


class CompleteSourceContextExceeded(ValueError):
    """Do not ask a model to review a truncated source payload."""


def complete_source_context(messages, protected, allowance, count):
    messages=[dict(message) for message in messages]
    for index in protected:
        payload=json.loads(messages[index]['content'])
        if not isinstance(payload.get('files'),dict) or not payload['files']:
            raise CompleteSourceContextExceeded('Complete source review requires nonempty files')
        design=payload.get('design')
        if isinstance(design,dict):
            for key in sorted(list(design),key=lambda key:count(design[key]),reverse=True):
                if count(messages)<=allowance:break
                design.pop(key)
                payload.setdefault('omittedDesignFields',[]).append(key)
                messages[index]['content']=json.dumps(payload,ensure_ascii=False)
    if count(messages)>allowance:
        raise CompleteSourceContextExceeded('Complete draft source and interfaces exceed the configured context budget; source was not truncated or sent for review')
    return messages


def bounded_messages(messages, tools, limit=None):
    from .progress import model_request_timeout
    model_request_timeout(120)
    # Token estimates include schemas and envelope overhead. Provider tokenizers
    # differ; retain a conservative margin rather than claiming billing accuracy.
    cap = min(48000, max(2000, int(os.getenv('GENESYS_INPUT_TOKEN_LIMIT', '48000'))))
    if limit is not None:
        cap = min(cap, limit)
    enc = encoding()
    def count(value):
        return len(enc.encode(json.dumps(value, ensure_ascii=False, default=str), disallowed_special=()))
    safe = text_safe(messages)
    protected=[i for i,message in enumerate(safe) if message.pop('_preserve_complete_source',False)]
    allowance = cap - count(tools) - 512
    if allowance < 512:
        raise ValueError('Tool schemas exceed the configured model input budget.')
    if count(safe) <= allowance:
        reserve_model_budget(2 * (count(safe) + count(tools) + 512 + 24000))
        return safe
    if protected:
        result=complete_source_context(safe,protected,allowance,count)
        reserve_model_budget(2 * (count(result) + count(tools) + 512 + 24000))
        return result
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
        # Count the serialized candidate, including JSON escaping and envelope
        # overhead. Raw content tokens alone can substantially undercount code.
        candidate = dict(item)
        while count([kept[key] for key in sorted(kept)] + [candidate]) > allowance:
            candidate_ids = enc.encode(candidate['content'], disallowed_special=())
            if len(candidate_ids) < 128:
                candidate = None
                break
            candidate = dict(candidate, content=enc.decode(candidate_ids[:max(64, len(candidate_ids) * 3 // 4)]))
        if candidate is not None:
            kept[index] = candidate
    result = [kept[index] for index in sorted(kept)]
    if count(result) > allowance:
        raise ValueError('Unable to fit context into the configured input budget.')
    reserve_model_budget(2 * (count(result) + count(tools) + 512 + 24000))
    return result
