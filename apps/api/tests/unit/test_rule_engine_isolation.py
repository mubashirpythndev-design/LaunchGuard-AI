"""Test isolation of rule_engine (Constitution 2.I).

The rule engine must NOT import anything from cv or agent.
"""
import ast
from pathlib import Path

RULE_ENGINE_DIR = Path(__file__).resolve().parent.parent.parent / "rule_engine"


def test_rule_engine_never_imports_cv_or_agent() -> None:
    """Walk AST of all rule_engine modules to assert zero imports from cv or agent."""
    py_files = list(RULE_ENGINE_DIR.glob("*.py"))
    assert len(py_files) > 0, "No rule_engine python files found"

    for file_path in py_files:
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".")[0]
                    assert root_name not in ("cv", "agent"), (
                        f"Prohibited import '{alias.name}' in {file_path.name} (Constitution 2.I)"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_name = node.module.split(".")[0]
                    assert root_name not in ("cv", "agent"), (
                        f"Prohibited from-import '{node.module}' in {file_path.name} "
                        "(Constitution 2.I)"
                    )
