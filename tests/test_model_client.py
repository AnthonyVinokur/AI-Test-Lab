from tests.fakes import FakeModelClient


def test_fake_model_client_returns_standardized_response() -> None:
    client = FakeModelClient(
        response_text="Hello",
        model="test-model",
    )

    response = client.generate("Say hello")

    assert response.content == "Hello"
    assert response.model == "test-model"
    assert response.prompt_tokens== 0
    # assert response.
    # assert response.metrics.response_tokens == 0