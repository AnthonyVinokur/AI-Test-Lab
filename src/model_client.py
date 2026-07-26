from abc import ABC, abstractmethod

from src.models import ModelResponse


class ModelClient(ABC):
    """
    Base interface for every AI model provider used by AI Test Lab.

    Every model client must implement the generate() method and return
    a standardized ModelResponse object.
    """

    @abstractmethod
    def generate(self, prompt: str) -> ModelResponse:
        """
        Send a prompt to the model and return a normalized response.

        Args:
            prompt: The text sent to the AI model.

        Returns:
            A ModelResponse containing the generated text, model name,
            and performance metrics.
        """
        raise NotImplementedError