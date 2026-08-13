from src.model_client import ModelClient
from src.models import ModelResponse, OllamaMetrics


class FakeModelClient(ModelClient):
    """
    Predictable model client used for unit tests.

    It avoids calling a real AI model, making tests faster,
    cheaper, and deterministic.
    """

    def __init__(
            self,
            response_text: str = "Hello from the fake model",
            model: str = "fake-model",
            provider: str = "fake",
            estimated_cost_usd: float = 0.0,
    ) -> None:
        self.response_text = response_text
        self.model = model
        self.provider = provider
        self.estimated_cost_usd = estimated_cost_usd

    def generate(self, prompt: str) -> ModelResponse:
        return ModelResponse(
            provider=self.provider,
            content=self.response_text,
            model=self.model,
            estimated_cost_usd=self.estimated_cost_usd,
            metrics=OllamaMetrics(),
        )