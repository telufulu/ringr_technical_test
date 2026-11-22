"""Run the whole test suite with a readable, colored output.

Usage, from any directory:

    python3 tests/run_tests.py

Tests are grouped by component (Agent, AssistanceAgent, DebtAgent,
HttpClient) using the first line of each TestCase docstring, written as
"Component · topic". Colors are disabled when the output is not a terminal
or when the NO_COLOR environment variable is set.

Generated with AI following the project design (see docs/ai_usage.md).
"""

import os
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TESTS_DIR.parent

USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"
# One color per component, assigned in order of appearance.
COMPONENT_COLORS = ["\033[36m", "\033[35m", "\033[34m", "\033[33m"]


def paint(text: str, *codes: str) -> str:
    if not USE_COLOR:
        return text
    return "".join(codes) + text + RESET


def group_title(test: unittest.TestCase) -> tuple[str, str]:
    """Return (component, topic) from the TestCase docstring."""
    doc = (type(test).__doc__ or "").strip().splitlines()
    title = doc[0] if doc else type(test).__name__
    component, _, topic = title.partition(" · ")
    return component, topic


def readable_name(test: unittest.TestCase) -> str:
    name = test._testMethodName.removeprefix("test_").replace("_", " ")
    return name[:1].upper() + name[1:]


class ReadableResult(unittest.TextTestResult):
    """Prints one line per test, grouped by component and topic."""

    def __init__(self, stream, descriptions, verbosity):
        # Verbosity 0 silences the default dots; this class prints its own lines.
        super().__init__(stream, descriptions, verbosity=0)
        self.current_component = None
        self.current_topic = None
        self.component_colors: dict[str, str] = {}

    def startTest(self, test):
        super().startTest(test)
        component, topic = group_title(test)
        if component != self.current_component:
            color = COMPONENT_COLORS[len(self.component_colors) % len(COMPONENT_COLORS)]
            self.component_colors[component] = color
            self.current_component = component
            self.current_topic = None
            self.stream.writeln()
            self.stream.writeln(paint(f"━━ {component} " + "━" * (60 - len(component)), BOLD, color))
        if topic and topic != self.current_topic:
            self.current_topic = topic
            self.stream.writeln(paint(f"  {topic}", self.component_colors[component]))

    def _line(self, symbol: str, color: str, test, detail: str = "") -> None:
        suffix = paint(f"  {detail}", DIM) if detail else ""
        self.stream.writeln(f"    {paint(symbol, BOLD, color)} {readable_name(test)}{suffix}")

    def addSuccess(self, test):
        super().addSuccess(test)
        self._line("✓", GREEN, test)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._line("✗", RED, test, "failed")

    def addError(self, test, err):
        super().addError(test, err)
        self._line("✗", RED, test, "error")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._line("-", YELLOW, test, f"skipped: {reason}")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self._line("✗", RED, test, f"failed case: {subtest._subDescription()}")


def main() -> int:
    # The project root makes `agents`, `config`... importable; discovery adds tests/.
    sys.path.insert(0, str(ROOT_DIR))
    suite = unittest.defaultTestLoader.discover(str(TESTS_DIR), top_level_dir=str(TESTS_DIR))
    runner = unittest.TextTestRunner(resultclass=ReadableResult, verbosity=0)
    result = runner.run(suite)

    summary = f"{result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors"
    color = GREEN if result.wasSuccessful() else RED
    print(paint(("✓ " if result.wasSuccessful() else "✗ ") + summary, BOLD, color))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
