import pytest
from agent.usage_limits import UsageLimiter, UsageLimited


def test_one_build_per_user_across_projects():
    limiter = UsageLimiter(cooldown=0)
    reservation = limiter.reserve('user')
    with pytest.raises(UsageLimited, match='already running'):
        limiter.reserve('user')
    limiter.reserve('other')
    limiter.release(reservation)
    assert not limiter.status('user')['buildRunning']


def test_hourly_limit_and_expiry():
    now = [100]
    limiter = UsageLimiter(hourly=1, daily=3, cooldown=0, clock=lambda: now[0])
    limiter.release(limiter.reserve('user'))
    with pytest.raises(UsageLimited, match='Hourly'):
        limiter.reserve('user')
    now[0] += 3601
    limiter.release(limiter.reserve('user'))
    assert limiter.status('user')['dailyRemaining'] == 1


def test_daily_limit_cooldown_and_refund():
    now = [0]
    limiter = UsageLimiter(hourly=5, daily=1, cooldown=10, clock=lambda: now[0])
    reservation = limiter.reserve('user')
    limiter.release(reservation, refund=True)
    assert limiter.status('user')['dailyRemaining'] == 1
    limiter.release(limiter.reserve('user'))
    with pytest.raises(UsageLimited, match='Daily'):
        limiter.reserve('user')
    now[0] = 86401
    limiter.release(limiter.reserve('user'))


def test_cooldown():
    now = [0]
    limiter = UsageLimiter(cooldown=10, clock=lambda: now[0])
    limiter.release(limiter.reserve('user'))
    with pytest.raises(UsageLimited, match='wait briefly'):
        limiter.reserve('user')
    now[0] = 11
    limiter.reserve('user')
