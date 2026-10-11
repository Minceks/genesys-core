"""Per-account model usage; admission limits never interrupt an accepted build."""
from contextvars import ContextVar
import json
import os
import time
from .beta_storage import connection

account_context = ContextVar('model_usage_account', default=None)


def exempt(user_id):
    return user_id in {x.strip() for x in os.getenv('GENESYS_UNLIMITED_USER_IDS', '').split(',') if x.strip()}


def allowance(user_id):
    overrides = json.loads(os.getenv('GENESYS_USER_TOKEN_LIMITS', '{}'))
    limit = None if exempt(user_id) else max(1, int(overrides.get(user_id, os.getenv('GENESYS_USER_DAILY_TOKEN_LIMIT', '250000'))))
    day = int(time.time() // 86400)
    with connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS user_model_usage(user_id TEXT, day INTEGER, tokens INTEGER NOT NULL, PRIMARY KEY(user_id,day))')
        row = db.execute('SELECT tokens FROM user_model_usage WHERE user_id=? AND day=?', (user_id, day)).fetchone()
    used = row[0] if row else 0
    return {'dailyTokenLimit':limit, 'dailyTokensUsed':used,
            'dailyTokensRemaining':None if limit is None else max(0,limit-used),
            'tokenResetAt':(day+1)*86400*1000, 'dailyUnlimited':exempt(user_id),
            'tokenUsageScope':'Provider-reported usage for successful model responses; failed requests may not report usage.'}


def record(response):
    user_id = account_context.get()
    if not user_id:
        return
    usage = getattr(response, 'usage', None) or getattr(response, 'usage_metadata', None)
    tokens = getattr(usage, 'total_tokens', None) or getattr(usage, 'total_token_count', None)
    if not isinstance(tokens, int) or tokens < 0:
        return
    day = int(time.time() // 86400)
    with connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS user_model_usage(user_id TEXT, day INTEGER, tokens INTEGER NOT NULL, PRIMARY KEY(user_id,day))')
        db.execute('INSERT INTO user_model_usage VALUES(?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET tokens=tokens+excluded.tokens', (user_id, day, tokens))
        db.execute('DELETE FROM user_model_usage WHERE day<?', (day-30,))
