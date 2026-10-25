import logging
from agent.logging_config import configure_logging


def test_http_transport_noise_keeps_warnings_and_debug_opt_in(monkeypatch):
    names=('httpx','httpx2','httpcore')
    before={name:logging.getLogger(name).level for name in names}
    root_level=logging.getLogger().level
    try:
        monkeypatch.setenv('GENESYS_LOG_LEVEL','INFO');configure_logging()
        for name in names:
            logger=logging.getLogger(name)
            assert not logger.isEnabledFor(logging.INFO)
            assert logger.isEnabledFor(logging.WARNING) and logger.isEnabledFor(logging.ERROR)
        monkeypatch.setenv('GENESYS_LOG_LEVEL','DEBUG');configure_logging()
        assert all(logging.getLogger(name).isEnabledFor(logging.DEBUG) for name in names)
    finally:
        for name,level in before.items():logging.getLogger(name).setLevel(level)
        logging.getLogger().setLevel(root_level)
