
from unittest.mock import MagicMock, call

import pytest

from app.llm.api_handler import generate_response
from app.llm.exceptions import (
    APIAuthenticationError,
    APIQuotaExceededError,
    APIServiceError,
    TracePilotAPIError,
)
from app.llm.response_handler import is_response_complete


@pytest.fixture
def setup_models(monkeypatch):
    """Prepare a fake Gemini environment without real API calls."""

    monkeypatch.setenv(
        "GEMINI_MODEL",
        "gemini-3.5-flash-lite",
    )
    monkeypatch.setenv(
        "GEMINI_MODEL_FALLBACK",
        "gemini-3.5-flash",
    )

    monkeypatch.setattr(
        "app.llm.api_handler.create_gemini_client",
        MagicMock(),
    )

    monkeypatch.setattr(
        "app.llm.api_handler.create_generation_config",
        MagicMock(return_value="fake_config"),
    )

    monkeypatch.setattr(
        "app.llm.api_handler.extract_response_text",
        MagicMock(return_value="Successful response"),
    )

    monkeypatch.setattr(
        "app.llm.api_handler.extract_response_metadata",
        MagicMock(
            return_value={
                "candidate_count": 1,
                "finish_reason": "STOP",
                "prompt_tokens": 50,
                "response_tokens": 50,
                "total_tokens": 100,
                "is_complete": True,
                "was_truncated": False,
            }
        ),
    )

    request_mock = MagicMock()

    monkeypatch.setattr(
        "app.llm.api_handler._request_model",
        request_mock,
    )

    return request_mock


def set_response_metadata(monkeypatch, finish_reason):
    """Configure mocked Gemini response metadata."""

    monkeypatch.setattr(
        "app.llm.api_handler.extract_response_metadata",
        MagicMock(
            return_value={
                "candidate_count": 1,
                "finish_reason": finish_reason,
                "prompt_tokens": 50,
                "response_tokens": 50,
                "total_tokens": 100,
                "is_complete": finish_reason == "STOP",
                "was_truncated": finish_reason == "MAX_TOKENS",
            }
        ),
    )


# --------------------------------------------------
# EXISTING MODEL FALLBACK TESTS
# --------------------------------------------------


def test_primary_model_success(setup_models):
    """Primary succeeds, so fallback must not run."""

    setup_models.return_value = MagicMock()

    result = generate_response("Test prompt")

    assert result == "Successful response"
    assert setup_models.call_count == 1

    assert setup_models.call_args[0][1] == (
        "gemini-3.5-flash-lite"
    )


def test_primary_quota_fallback(setup_models):
    """Primary quota failure should trigger fallback."""

    setup_models.side_effect = [
        APIQuotaExceededError("Daily quota exhausted"),
        MagicMock(),
    ]

    result = generate_response("Test prompt")

    assert result == "Successful response"
    assert setup_models.call_count == 2

    assert setup_models.call_args_list == [
        call(
            setup_models.call_args_list[0][0][0],
            "gemini-3.5-flash-lite",
            "Test prompt",
            "fake_config",
        ),
        call(
            setup_models.call_args_list[1][0][0],
            "gemini-3.5-flash",
            "Test prompt",
            "fake_config",
        ),
    ]


def test_primary_server_failure_fallback(setup_models):
    """Server failure should trigger fallback."""

    setup_models.side_effect = [
        APIServiceError("Server unavailable"),
        MagicMock(),
    ]

    result = generate_response("Test prompt")

    assert result == "Successful response"
    assert setup_models.call_count == 2

    assert setup_models.call_args_list[0].args[1] == (
        "gemini-3.5-flash-lite"
    )

    assert setup_models.call_args_list[1].args[1] == (
        "gemini-3.5-flash"
    )


def test_authentication_error_no_fallback(setup_models):
    """Authentication errors must not trigger fallback."""

    setup_models.side_effect = APIAuthenticationError(
        "Invalid API key"
    )

    with pytest.raises(APIAuthenticationError):
        generate_response("Test prompt")

    assert setup_models.call_count == 1


def test_both_models_fail(setup_models):
    """If both models fail, return a clear TracePilot error."""

    setup_models.side_effect = [
        APIQuotaExceededError("Primary quota exhausted"),
        APIServiceError("Fallback unavailable"),
    ]

    with pytest.raises(
        TracePilotAPIError,
        match="Both primary and fallback",
    ):
        generate_response("Test prompt")

    assert setup_models.call_count == 2


# --------------------------------------------------
# PHASE 5.3: RESPONSE TRUNCATION TESTS
# --------------------------------------------------



def test_primary_truncated_fallback_success(
    setup_models,
    monkeypatch,
):
    """A truncated primary response should trigger fallback."""

    metadata_mock = MagicMock(
        side_effect=[
            {
                "candidate_count": 1,
                "finish_reason": "MAX_TOKENS",
                "prompt_tokens": 50,
                "response_tokens": 2048,
                "total_tokens": 2098,
                "is_complete": False,
                "was_truncated": True,
            },
            {
                "candidate_count": 1,
                "finish_reason": "STOP",
                "prompt_tokens": 50,
                "response_tokens": 100,
                "total_tokens": 150,
                "is_complete": True,
                "was_truncated": False,
            },
        ]
    )

    monkeypatch.setattr(
        "app.llm.api_handler.extract_response_metadata",
        metadata_mock,
    )

    setup_models.side_effect = [
        MagicMock(),
        MagicMock(),
    ]

    result = generate_response("Test prompt")

    assert result == "Successful response"
    assert setup_models.call_count == 2
    assert metadata_mock.call_count == 2

    assert setup_models.call_args_list[0].args[1] == (
        "gemini-3.5-flash-lite"
    )

    assert setup_models.call_args_list[1].args[1] == (
        "gemini-3.5-flash"
    )



def test_both_models_truncated(setup_models, monkeypatch):
    """Both truncated responses should produce a clear error."""

    set_response_metadata(monkeypatch, "MAX_TOKENS")

    setup_models.side_effect = [
        MagicMock(),
        MagicMock(),
    ]

    with pytest.raises(
        TracePilotAPIError,
        match="Both primary and fallback",
    ):
        generate_response("Test prompt")

    assert setup_models.call_count == 2


def test_primary_normal_completion(
    setup_models,
    monkeypatch,
):
    """A normal STOP response should not trigger fallback."""

    set_response_metadata(monkeypatch, "STOP")

    setup_models.return_value = MagicMock()

    result = generate_response("Test prompt")

    assert result == "Successful response"
    assert setup_models.call_count == 1


def test_unexpected_finish_reason_does_not_mark_complete():
    """Unexpected finish reasons must not be marked complete."""

    candidate = MagicMock()
    candidate.finish_reason = "SAFETY"

    response = MagicMock()
    response.candidates = [candidate]

    assert is_response_complete(response) is False
