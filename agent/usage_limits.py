"""Thread-safe rolling beta limits for the current backend replica."""

from collections import deque
import os
import threading
import time


class UsageLimited(ValueError):
    def __init__(self, message, retry_after):
        super().__init__(message)
        self.retry_after = max(1, int(retry_after))


class UsageLimiter:
    def __init__(self, hourly=None, daily=None, cooldown=None, clock=time.monotonic):
        self.hourly = max(1, int(hourly if hourly is not None else os.getenv('GENESYS_BUILDS_PER_HOUR', '5')))
        self.daily = max(1, int(daily if daily is not None else os.getenv('GENESYS_BUILDS_PER_DAY', '20')))
        self.cooldown = max(0, int(cooldown if cooldown is not None else os.getenv('GENESYS_BUILD_COOLDOWN_SECONDS', '10')))
        self.clock, self.lock, self.records, self.active = clock, threading.Lock(), {}, set()

    def reserve(self, user_id):
        with self.lock:
            now = self.clock()
            self.records = {user: deque(value for value in history if now - value < 86400)
                            for user, history in self.records.items() if history and now - history[-1] < 86400}
            history = self.records.get(user_id, deque())
            if user_id in self.active:
                raise UsageLimited('One build is already running for your account. Wait for it to finish.', 10)
            hourly = [value for value in history if now - value < 3600]
            if len(history) >= self.daily:
                raise UsageLimited('Daily beta build limit reached. Please return later.', 86400 - (now - history[0]))
            if len(hourly) >= self.hourly:
                raise UsageLimited('Hourly beta build limit reached. Please return later.', 3600 - (now - hourly[0]))
            if history and now - history[-1] < self.cooldown:
                raise UsageLimited('Please wait briefly before starting another build.', self.cooldown - (now - history[-1]))
            self.records[user_id] = history
            history.append(now)
            self.active.add(user_id)
            return (user_id, now)

    def release(self, reservation, refund=False):
        if reservation is None:
            return
        user_id, timestamp = reservation
        with self.lock:
            self.active.discard(user_id)
            if refund:
                try:
                    self.records[user_id].remove(timestamp)
                except (KeyError, ValueError):
                    pass

    def status(self, user_id):
        with self.lock:
            now = self.clock()
            history = self.records.get(user_id, ())
            return {'hourlyLimit': self.hourly, 'dailyLimit': self.daily,
                    'hourlyRemaining': max(0, self.hourly - sum(now - value < 3600 for value in history)),
                    'dailyRemaining': max(0, self.daily - sum(now - value < 86400 for value in history)),
                    'buildRunning': user_id in self.active, 'scope': 'current backend replica'}
