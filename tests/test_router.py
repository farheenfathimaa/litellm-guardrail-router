from unittest.mock import MagicMock, patch

import pytest

from app.router import RoutingError, route_request


def _mock_response(content="Hello", provider="test", prompt_tokens=10, completion_tokens=20):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = content
    mock_resp.model = f"{provider}/model"
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = prompt_tokens
    mock_resp.usage.completion_tokens = completion_tokens
    mock_resp.usage.total_tokens = prompt_tokens + completion_tokens
    return mock_resp


class TestRouteRequest:
    @patch("app.router._bedrock_available", return_value=True)
    @patch("app.router.litellm.completion")
    def test_bedrock_primary_success(self, mock_completion, mock_bedrock):
        mock_completion.return_value = _mock_response("Bedrock answer", "bedrock")
        result = route_request([{"role": "user", "content": "hi"}])
        assert result["provider"] == "bedrock"
        assert result["content"] == "Bedrock answer"
        assert result["input_tokens"] == 10
        assert result["output_tokens"] == 20
        mock_completion.assert_called_once()

    @patch("app.router._bedrock_available", return_value=False)
    @patch("app.router.litellm.completion")
    def test_bedrock_auth_failure_falls_to_groq(self, mock_completion, mock_bedrock):
        mock_completion.return_value = _mock_response("Groq answer", "groq")
        result = route_request([{"role": "user", "content": "hi"}])
        assert result["provider"] == "groq"
        assert result["content"] == "Groq answer"

    @patch("app.router._bedrock_available", return_value=False)
    @patch("app.router.litellm.completion")
    def test_bedrock_and_groq_fail_falls_to_gemini(self, mock_completion, mock_bedrock):
        def side_effect(model, messages, max_tokens):
            if "groq" in model:
                raise Exception("Groq down")
            return _mock_response("Gemini answer", "gemini")

        mock_completion.side_effect = side_effect
        result = route_request([{"role": "user", "content": "hi"}])
        assert result["provider"] == "gemini"
        assert result["content"] == "Gemini answer"

    @patch("app.router._bedrock_available", return_value=False)
    @patch("app.router.litellm.completion")
    def test_all_providers_fail_raises_error(self, mock_completion, mock_bedrock):
        mock_completion.side_effect = Exception("Everything broken")
        with pytest.raises(RoutingError, match="All providers exhausted"):
            route_request([{"role": "user", "content": "hi"}])

    @patch("app.router._bedrock_available", return_value=True)
    @patch("app.router.litellm.completion")
    def test_bedrock_runtime_error_falls_to_groq(self, mock_completion, mock_bedrock):
        call_count = [0]

        def side_effect(model, messages, max_tokens):
            call_count[0] += 1
            if "bedrock" in model:
                raise Exception("429 Too Many Requests")
            return _mock_response("Groq fallback", "groq")

        mock_completion.side_effect = side_effect
        result = route_request([{"role": "user", "content": "hi"}])
        assert result["provider"] == "groq"

    @patch("app.router._bedrock_available", return_value=True)
    @patch("app.router.litellm.completion")
    def test_bedrock_auth_error_falls_to_groq(self, mock_completion, mock_bedrock):
        def side_effect(model, messages, max_tokens):
            if "bedrock" in model:
                raise Exception("Invalid credentials provided")
            return _mock_response("Groq after auth fail", "groq")

        mock_completion.side_effect = side_effect
        result = route_request([{"role": "user", "content": "hi"}])
        assert result["provider"] == "groq"
