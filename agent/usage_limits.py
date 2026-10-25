from .user_allowance import allowance, exempt
"""Persistent rolling build limits with durable job awareness."""
import os
import threading
import time
from .beta_storage import connection

class UsageLimited(ValueError):
    def __init__(self, message, retry_after):
        super().__init__(message)
        self.retry_after = max(1, int(retry_after))

class UsageLimiter:
    def __init__(self, hourly=None, daily=None, cooldown=None, clock=time.time):
        self.hourly = max(1, int(hourly if hourly is not None else os.getenv('GENESYS_BUILDS_PER_HOUR', '5')))
        self.daily = max(1, int(daily if daily is not None else os.getenv('GENESYS_BUILDS_PER_DAY', '20')))
        self.cooldown = max(0, int(cooldown if cooldown is not None else os.getenv('GENESYS_BUILD_COOLDOWN_SECONDS', '10')))
        self.clock, self.lock, self.active = clock, threading.Lock(), set()
        with connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS build_usage(user_id TEXT, created REAL, PRIMARY KEY(user_id,created))')

    def running(self, db, user_id):
        if user_id in self.active:
            return True
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone():
            return False
        return bool(db.execute("SELECT 1 FROM jobs WHERE user_id=? AND state IN ('queued','running') LIMIT 1", (user_id,)).fetchone())

    def reserve(self, user_id):
        tokens = allowance(user_id)
        with self.lock, connection() as db:
            db.execute('BEGIN IMMEDIATE')
            now = self.clock()
            db.execute('DELETE FROM build_usage WHERE created < ?', (now-86400,))
            history = [row[0] for row in db.execute('SELECT created FROM build_usage WHERE user_id=? ORDER BY created', (user_id,))]
            if self.running(db, user_id):
                raise UsageLimited('One build is already running for your account. Wait for it to finish.', 10)
            hourly = [value for value in history if now-value < 3600]
            if not exempt(user_id) and tokens['dailyTokensRemaining'] < int(os.getenv('GENESYS_BUILD_TOKEN_HEADROOM', '50000')):
                raise UsageLimited('Daily account allowance is too low to start another build. Existing builds can finish.', tokens['tokenResetAt']/1000-now)
            if not exempt(user_id) and len(history) >= self.daily:
                raise UsageLimited('Daily beta build limit reached. Please return later.', 86400-(now-history[0]))
            if len(hourly) >= self.hourly:
                raise UsageLimited('Hourly beta build limit reached. Please return later.', 3600-(now-hourly[0]))
            if history and now-history[-1] < self.cooldown:
                raise UsageLimited('Please wait briefly before starting another build.', self.cooldown-(now-history[-1]))
            db.execute('INSERT INTO build_usage VALUES(?,?)', (user_id, now))
            self.active.add(user_id)
            return (user_id, now)

    def release(self, reservation, refund=False):
        if reservation is None:
            return
        user_id, timestamp = reservation
        with self.lock, connection() as db:
            self.active.discard(user_id)
            if refund:
                db.execute('DELETE FROM build_usage WHERE user_id=? AND created=?', (user_id, timestamp))

    def status(self, user_id):
        with self.lock, connection() as db:
            now = self.clock()
            history = [row[0] for row in db.execute('SELECT created FROM build_usage WHERE user_id=? AND created>?', (user_id, now-86400))]
            return {'hourlyLimit':self.hourly,'dailyLimit':self.daily,
                    'hourlyRemaining':max(0,self.hourly-sum(now-value<3600 for value in history)),
                    'dailyRemaining':None if exempt(user_id) else max(0,self.daily-len(history)),
                    **allowance(user_id),
                    'buildRunning':self.running(db,user_id),'scope':'persistent backend accounting'}
