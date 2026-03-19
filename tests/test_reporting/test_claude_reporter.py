from unittest.mock import patch, MagicMock
from tecs.reporting.claude_reporter import ClaudeReporter


def test_generate_report_calls_subprocess():
    reporter = ClaudeReporter(enabled=True)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="# Report\nTest report", returncode=0)
        result = reporter.generate_report({"phase": 1, "best_fitness": 0.5}, prompt_prefix="분석해:")
        assert "Report" in result
        mock_run.assert_called_once()


def test_generate_report_disabled():
    reporter = ClaudeReporter(enabled=False)
    result = reporter.generate_report({"phase": 1}, prompt_prefix="분석:")
    assert result == ""


def test_generate_report_fallback_on_error():
    reporter = ClaudeReporter(enabled=True)
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = reporter.generate_report({"phase": 1}, prompt_prefix="분석:")
        assert result == ""
