"""Optional in-process adapter for Aquagear's existing RAG application path."""

from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from src.models import ModelResponse


class AquagearExecutionError(RuntimeError):
    """Aquagear did not produce a usable application response."""


class AquagearClient:
    """Implement TestRunner's client protocol without bypassing Aquagear RAG.

    Aquagear is optional and imported only when this client is configured.
    Receipts are an explicit allow-list, not serialized application internals.
    """

    def __init__(self, executor, *, model: str, top_k: int = 1,
                 failure_mode: str = "none") -> None:
        from reference_app.rag_failures import RAGFailureMode

        if not model.strip():
            raise ValueError("model must not be empty")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        self.executor = executor
        self.model = model
        self.top_k = top_k
        self.failure_mode = RAGFailureMode(failure_mode)
        self.receipts: list[dict] = []

    def generate(self, prompt: str) -> ModelResponse:
        from reference_app.rag_executor import RAGExecutionRequest

        request = RAGExecutionRequest(
            execution_id=f"atl-{uuid4()}", question=prompt,
            top_k=self.top_k, failure_mode=self.failure_mode,
        )
        started = perf_counter()
        receipt = {
            "execution_id": request.execution_id,
            "question": prompt,
            "application_received": False,
            "status": "error",
            "response": None,
            "retrieved_document_ids": [],
            "failure_mode": self.failure_mode.value,
        }
        try:
            result = self.executor.execute(request)
            if result.execution_id != request.execution_id or result.question != prompt:
                raise AquagearExecutionError("Aquagear response identity mismatch")
            receipt["application_received"] = True
            receipt["retrieved_document_ids"] = [
                item.document.id for item in result.retrieval_result.documents
            ]
            if not result.completed:
                error = result.execution_result.error
                kind = error.error_type if error is not None else "ExecutionError"
                raise AquagearExecutionError(f"Aquagear execution failed ({kind})")
            if not isinstance(result.response, str) or not result.response.strip():
                raise AquagearExecutionError("Aquagear returned an empty or invalid answer")
            receipt.update(status="completed", response=result.response)
            return ModelResponse(
                provider="aquagear", model=self.model, content=result.response,
                response_time_seconds=max(0.0, perf_counter() - started),
            )
        except Exception as exc:
            # Do not copy arbitrary provider exception strings (URLs/secrets)
            # into public reports or the allow-listed receipt.
            message = (str(exc) if isinstance(exc, AquagearExecutionError)
                       else f"Aquagear execution failed ({type(exc).__name__})")
            receipt["error"] = message
            raise AquagearExecutionError(message) from exc
        finally:
            receipt["duration_seconds"] = max(0.0, perf_counter() - started)
            self.receipts.append(receipt)


def build_aquagear_client(*, mode: str = "ollama", model: str = "llama3.1:latest",
                          top_k: int = 1, failure_mode: str = "none") -> AquagearClient:
    """Use the same RAG components as Aquagear app.py; no Streamlit import."""
    from reference_app.context_builder import DeterministicContextBuilder
    from reference_app.knowledge import KNOWLEDGE_DOCUMENTS
    from reference_app.rag_executor import RAGExecutor
    from reference_app.retrieval import ControlledRetriever
    from reference_app.scenario_execution import ScenarioExecutor

    if mode == "controlled":
        from reference_app.ci_model import generate_controlled_ci_response
        generate = generate_controlled_ci_response
        model_identity = "aquagear-controlled-ci"
    elif mode == "ollama":
        from reference_app.ollama_model import ControlledOllamaModel
        generate = ControlledOllamaModel(model_name=model).generate
        model_identity = model
    else:
        raise ValueError("mode must be controlled or ollama")

    return AquagearClient(
        RAGExecutor(
            retriever=ControlledRetriever(KNOWLEDGE_DOCUMENTS),
            context_builder=DeterministicContextBuilder(),
            scenario_executor=ScenarioExecutor(generate),
        ),
        model=model_identity, top_k=top_k, failure_mode=failure_mode,
    )
