from openai import OpenAI
from reachai.core.config import settings


class LLMClient:
    """Generic OpenAI-compatible LLM abstraction.

    Supports LM Studio, OpenRouter, OpenAI, Anthropic, Google Gemini,
    and any other provider exposing an OpenAI-compatible chat completions endpoint.
    Switch providers by changing .env variables only.
    """

    def __init__(self):
        self.client = OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
        )
        self.model = settings.LLM_MODEL

    def chat(self, messages, temperature=0.2, max_tokens=1024):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
