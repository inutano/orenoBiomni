"""Tests for SSE event parser — the most critical parsing logic."""

import pytest
from unittest.mock import MagicMock


def _make_ai_msg(content: str):
    """Create a mock AIMessage."""
    msg = MagicMock()
    msg.content = content
    # Make isinstance checks work
    msg.__class__.__name__ = "AIMessage"
    return msg


def _parse(content: str) -> list[dict]:
    """Parse content through the event parser."""
    from langchain_core.messages import AIMessage
    from backend.app.services.agent_manager import _parse_message_to_events

    msg = AIMessage(content=content)
    return _parse_message_to_events(msg)


class TestThinkingParsing:
    def test_thinking_tag(self):
        events = _parse("<thinking>Let me analyze this</thinking>")
        assert len(events) == 1
        assert events[0]["event"] == "thinking"
        assert events[0]["data"]["content"] == "Let me analyze this"

    def test_think_tag(self):
        events = _parse("<think>Short form</think>")
        assert len(events) == 1
        assert events[0]["event"] == "thinking"

    def test_unclosed_thinking(self):
        events = _parse("<thinking>Still thinking...")
        assert len(events) == 1
        assert events[0]["event"] == "thinking"


class TestSolutionParsing:
    def test_solution_tag(self):
        events = _parse("<solution>Here is the answer</solution>")
        assert any(e["event"] == "solution" for e in events)
        solution = next(e for e in events if e["event"] == "solution")
        assert solution["data"]["content"] == "Here is the answer"

    def test_unclosed_solution(self):
        events = _parse("<solution>Partial answer")
        assert any(e["event"] == "solution" for e in events)

    def test_prose_mention_ignored(self):
        """Tags mentioned in prose (not at line start) should be ignored."""
        events = _parse('I should use the <solution> tag to respond.\n<solution>Real answer</solution>')
        solutions = [e for e in events if e["event"] == "solution"]
        assert len(solutions) == 1
        assert solutions[0]["data"]["content"] == "Real answer"


class TestExecuteParsing:
    def test_execute_tag(self):
        events = _parse("<execute>\n#!PYTHON\nprint('hello')\n</execute>")
        assert any(e["event"] == "execute" for e in events)

    def test_untagged_python_code(self):
        events = _parse("#!PYTHON\nprint('hello')")
        assert any(e["event"] == "execute" for e in events)

    def test_untagged_bash_code(self):
        events = _parse("#!BASH\nls -la")
        assert any(e["event"] == "execute" for e in events)


class TestCombinedParsing:
    def test_thinking_then_solution(self):
        content = "<thinking>Let me think</thinking>\n<solution>The answer is 42</solution>"
        events = _parse(content)
        types = [e["event"] for e in events]
        assert "thinking" in types
        assert "solution" in types

    def test_thinking_then_execute(self):
        content = "<thinking>I'll run code</thinking>\n<execute>\n#!PYTHON\nx=1\n</execute>"
        events = _parse(content)
        types = [e["event"] for e in events]
        assert "thinking" in types
        assert "execute" in types

    def test_suppressed_untagged_content(self):
        """Untagged AI content should be suppressed (failed parse attempt)."""
        events = _parse("Just some random text without any tags.")
        assert len(events) == 0


class TestObservation:
    def test_observation_tag(self):
        events = _parse("<observation>Error: file not found</observation>")
        assert len(events) == 1
        assert events[0]["event"] == "thinking"


class TestErrorDetection:
    def test_parsing_error(self):
        events = _parse("parsing error in response")
        assert any(e["event"] == "error" for e in events)
