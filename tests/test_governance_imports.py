"""Import boundary enforcement — scans all Python source files for forbidden ML imports.

WHY:  Prevents AI sessions or contributors from accidentally adding ML framework imports
      that violate the runtime/engine separation boundary.
RISK: Without this, someone could add `import torch` to scheduler.py and the runtime
      would silently gain an ML dependency.
"""

import ast
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"

FORBIDDEN_IMPORTS = frozenset({
    "torch",
    "tensorflow",
    "tf",
    "keras",
    "onnxruntime",
    "diffusers",
    "transformers",
    "whisper",
    "mediapipe",
    "ultralytics",
    "cv2",
    "openai_whisper",
    "stable_diffusion",
    "accelerate",
    "safetensors",
    "onnx",
})

FORBIDDEN_FROM_IMPORTS = frozenset({
    "torch",
    "tensorflow",
    "keras",
    "onnxruntime",
    "diffusers",
    "transformers",
    "whisper",
    "mediapipe",
    "ultralytics",
    "cv2",
    "openai_whisper",
    "accelerate",
    "safetensors",
    "onnx",
})


def _scan_file(path: Path) -> list[str]:
    """Parse a Python file and return list of forbidden imports found."""
    violations = []
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return [f"SYNTAX ERROR in {path}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split(".")[0]
                if root_module in FORBIDDEN_IMPORTS:
                    violations.append(f"line {node.lineno}: import {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_module = node.module.split(".")[0]
                if root_module in FORBIDDEN_FROM_IMPORTS:
                    violations.append(f"line {node.lineno}: from {node.module} import ...")

    return violations


def _get_python_files() -> list[Path]:
    return list(SRC_DIR.rglob("*.py"))


def test_no_forbidden_ml_imports():
    """Every .py file under src/ must not import any ML framework."""
    files = _get_python_files()
    assert len(files) > 0, "No Python files found in src/"

    all_violations = {}
    for f in files:
        violations = _scan_file(f)
        if violations:
            all_violations[str(f.relative_to(SRC_DIR.parent.parent))] = violations

    if all_violations:
        lines = ["FORBIDDEN ML IMPORTS DETECTED:"]
        for filepath, vlist in all_violations.items():
            for v in vlist:
                lines.append(f"  {filepath}: {v}")
        pytest.fail("\n".join(lines))


def test_forbidden_import_list_not_empty():
    """Safety check — the forbidden list must contain entries."""
    assert len(FORBIDDEN_IMPORTS) > 0
    assert len(FORBIDDEN_FROM_IMPORTS) > 0
