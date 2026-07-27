from __future__ import annotations

from typing import Any
from src.models import PromptTest
from .models import DatasetEntry


def prompt_test_to_dataset_entry(prompt_test: PromptTest) -> DatasetEntry:
    assertion_type = prompt_test.assertion.type
    normalized = assertion_type.value if hasattr(assertion_type, "value") else str(assertion_type)
    return DatasetEntry(
        id=str(prompt_test.id), name=prompt_test.name, input=prompt_test.prompt,
        expected_output=prompt_test.assertion.expected, category=prompt_test.category,
        metadata={"assertion_type": normalized, "expected": prompt_test.assertion.expected},
    )


def dataset_entry_to_prompt_dict(entry: DatasetEntry) -> dict[str, Any]:
    assertion_type = entry.metadata.get("assertion_type", "contains")
    expected = entry.metadata.get("expected", entry.expected_output)
    if expected is None:
        raise ValueError(f"Dataset entry '{entry.name}' does not define an expected value.")
    return {
        "id": entry.id,
        "name": entry.name,
        "category": entry.category,
        "prompt": entry.input,
        "assertion": {"type": assertion_type, "expected": expected},
    }


def dataset_entry_to_prompt_test(entry: DatasetEntry) -> PromptTest:
    return PromptTest.model_validate(dataset_entry_to_prompt_dict(entry))
