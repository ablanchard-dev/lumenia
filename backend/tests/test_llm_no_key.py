"""With no LLM key at all, the operator must see it at startup.

Before: missing keys were only logged at INFO, invisible under a default uvicorn run;
the only visible symptom was the chat saying "retry in a minute", forever.
"""
import logging

from app import llm


def test_no_llm_key_warns_at_startup(monkeypatch, caplog):
    for cfg in llm._PROVIDERS.values():
        for env in cfg["key_envs"]:
            monkeypatch.delenv(env, raising=False)
    with caplog.at_level(logging.WARNING, logger=llm.log.name):
        assert llm._build_chain() == []
    assert any(r.levelno >= logging.WARNING and ".env" in r.getMessage() for r in caplog.records)
