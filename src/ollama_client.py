from collections.abc import Callable
from typing import Any

import ollama

from src.model_client import ModelClient
from src.models import ModelResponse, OllamaMetrics

NANOSECONDS_PER_SECOND = 1_000_000_000


class OllamaClient(ModelClient):
    """Sends prompts to an Ollama model and collects performance metrics."""

    # def __init__(
    #     self,
    #     model: str = "llama3.1:latest",
    #     chat_function: Callable[..., dict[str, Any]] | None = None,
    # ) -> None:
    #     self.model = model
    #     self.chat_function = chat_function or ollama.chat
    def __init__(
            self,
            model: str = "llama3.1:latest",
            chat_function=ollama.chat,
    ) -> None:
        self.model = model
        self.chat_function = chat_function

    def generate(self, prompt: str) -> ModelResponse:
        data = self.chat_function(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            stream=False,
        )

        message = data.get("message", {})
        response_text = message.get("content", "")

        prompt_tokens = int(data.get("prompt_eval_count", 0))
        response_tokens = int(data.get("eval_count", 0))

        prompt_seconds = self._to_seconds(
            data.get("prompt_eval_duration", 0)
        )
        generation_seconds = self._to_seconds(
            data.get("eval_duration", 0)
        )

        metrics = OllamaMetrics(
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            prompt_latency_seconds=prompt_seconds,
            generation_latency_seconds=generation_seconds,
            total_latency_seconds=self._to_seconds(
                data.get("total_duration", 0)
            ),
            model_load_seconds=self._to_seconds(
                data.get("load_duration", 0)
            ),
            prompt_tokens_per_second=self._tokens_per_second(
                prompt_tokens,
                prompt_seconds,
            ),
            generation_tokens_per_second=self._tokens_per_second(
                response_tokens,
                generation_seconds,
            ),
        )


        return ModelResponse(
            provider="ollama",
            content=response_text,
            model=data.get("model", self.model),
            estimated_cost_usd=0.0,

            response_time_seconds=metrics.total_latency_seconds,
            prompt_tokens=metrics.prompt_tokens,
            output_tokens=metrics.response_tokens,
            prompt_latency_seconds=metrics.prompt_latency_seconds,
            generation_latency_seconds=metrics.generation_latency_seconds,
            model_load_seconds=metrics.model_load_seconds,
            prompt_tokens_per_second=metrics.prompt_tokens_per_second,
            generation_tokens_per_second=metrics.generation_tokens_per_second,
        )

    @staticmethod
    def _to_seconds(nanoseconds: int | float) -> float:
        return float(nanoseconds) / NANOSECONDS_PER_SECOND

    @staticmethod
    def _tokens_per_second(
        token_count: int,
        duration_seconds: float,
    ) -> float:
        if duration_seconds <= 0:
            return 0.0

        return token_count / duration_seconds