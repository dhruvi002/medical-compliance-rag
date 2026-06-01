import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .settings import Settings


@dataclass
class LLMResponse:
    content: str
    truncated: bool
    model: str
    latency_ms: float


class LLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str, settings: Settings) -> LLMResponse: ...


class OllamaClient(LLMClient):
    def complete(self, prompt: str, settings: Settings) -> LLMResponse:
        import ollama

        t0 = time.monotonic()
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            options={
                "num_predict": settings.max_tokens,
                "temperature": settings.temperature,
                "top_p": settings.top_p,
            },
        )
        latency_ms = (time.monotonic() - t0) * 1000
        truncated = response.get("done_reason") == "length"
        content = response["message"]["content"]
        return LLMResponse(
            content=content,
            truncated=truncated,
            model=settings.ollama_model,
            latency_ms=latency_ms,
        )


class GroqClient(LLMClient):
    def complete(self, prompt: str, settings: Settings) -> LLMResponse:
        import groq as groq_sdk

        t0 = time.monotonic()
        client = groq_sdk.Groq()
        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            top_p=settings.top_p,
        )
        latency_ms = (time.monotonic() - t0) * 1000
        choice = completion.choices[0]
        truncated = choice.finish_reason == "length"
        content = choice.message.content
        return LLMResponse(
            content=content,
            truncated=truncated,
            model=settings.groq_model,
            latency_ms=latency_ms,
        )


def get_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_backend == "groq":
        return GroqClient()
    return OllamaClient()
