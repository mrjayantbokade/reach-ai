import pytest
from reachai.core.config import settings
from reachai.llm.client import LLMClient


def test_settings_load():
    assert settings.LLM_PROVIDER == "openai_compatible"
    assert settings.LLM_MODEL is not None


def test_llm_client_exists():
    client = LLMClient()
    assert client.model is not None
