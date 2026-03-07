"""Tests for ClaudeClient — mocks Anthropic SDK."""
import pytest
from unittest.mock import MagicMock, patch
from apps.scoring.services.claude_client import ClaudeClient


def _mock_message(text: str, input_tokens: int = 100, output_tokens: int = 50):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    msg.usage.input_tokens = input_tokens
    msg.usage.output_tokens = output_tokens
    return msg


class TestClaudeClient:
    def _client(self):
        with patch("apps.scoring.services.claude_client.anthropic.Anthropic"):
            c = ClaudeClient()
        return c

    def test_parses_clean_json(self):
        client = self._client()
        payload = '"overall_score": 75, "summary": "test"}'
        client._client.messages.create.return_value = _mock_message(payload)
        result = client.complete("sys", "user")
        assert result["overall_score"] == 75
        assert "model_used" in result
        assert "api_cost_cents" in result

    def test_extract_json_strips_markdown_fences(self):
        payload = '```json\n{"overall_score": 50}\n```'
        result = ClaudeClient._extract_json(payload)
        assert result["overall_score"] == 50

    def test_raises_on_invalid_json(self):
        client = self._client()
        client._client.messages.create.return_value = _mock_message("not json at all")
        with pytest.raises(ValueError, match="not valid JSON"):
            client.complete("sys", "user")

    def test_cost_calculation(self):
        # 100 input tokens @ $3/M + 50 output tokens @ $15/M
        # = 0.03 cents + 0.075 cents = 0.105 cents → rounds to 1 cent (min)
        cost = ClaudeClient._calc_cost(100, 50)
        assert cost >= 1  # minimum 1 cent

        # Large token counts should produce meaningful cost
        cost_large = ClaudeClient._calc_cost(100_000, 5_000)
        # 100k input @ 300 cents/M + 5k output @ 1500 cents/M = 30 + 7.5 = 37.5 cents
        assert cost_large == 38

    def test_metadata_keys_added(self):
        client = self._client()
        client._client.messages.create.return_value = _mock_message('"x": 1}', 200, 100)
        result = client.complete("sys", "user")
        assert result["model_used"] is not None
        assert result["prompt_tokens"] == 200
        assert result["completion_tokens"] == 100
        assert isinstance(result["api_cost_cents"], int)
