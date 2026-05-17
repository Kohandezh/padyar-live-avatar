"""Dependency enforcement — ensures forbidden packages are not installed.

WHY:  Catches forbidden packages even if they enter via transitive dependencies
      or manual pip install. Runtime deps must stay minimal.
RISK:  A transitive dep could pull in torch (e.g., some utility package depends on it).
      This test catches that before it reaches production.
"""

import subprocess

import pytest

FORBIDDEN_PACKAGES = frozenset({
    "torch",
    "tensorflow",
    "onnxruntime",
    "diffusers",
    "transformers",
    "whisper",
    "mediapipe",
    "ultralytics",
    "keras",
    "openai-whisper",
    "stable-diffusion",
    "accelerate",
    "safetensors",
})


def _get_installed_packages() -> set[str]:
    result = subprocess.run(
        ["python", "-m", "pip", "list", "--format=freeze"],
        capture_output=True,
        text=True,
    )
    packages = set()
    for line in result.stdout.strip().split("\n"):
        if "==" in line:
            name = line.split("==")[0].lower().replace("-", "_")
            packages.add(name)
    return packages


def test_no_forbidden_packages_installed():
    """Installed packages must not include any ML frameworks."""
    installed = _get_installed_packages()
    violations = set()

    for pkg in FORBIDDEN_PACKAGES:
        normalized = pkg.lower().replace("-", "_")
        if normalized in installed:
            violations.add(pkg)

    if violations:
        pytest.fail(
            f"FORBIDDEN PACKAGES INSTALLED: {', '.join(sorted(violations))}\n"
            f"These packages violate the runtime boundary. Remove them from dependencies."
        )


def test_runtime_deps_are_minimal():
    """pyproject.toml dependencies must only contain approved packages."""

    approved_runtime_deps = {"fastapi", "uvicorn", "pydantic", "starlette", "anyio"}

    result = subprocess.run(
        ["python", "-m", "pip", "show", "padyar-live-avatar"],
        capture_output=True,
        text=True,
    )

    # Verify our direct deps are in the approved set
    for line in result.stdout.strip().split("\n"):
        if line.startswith("Requires:"):
            deps_str = line.split(":", 1)[1].strip()
            if deps_str:
                deps = [d.strip().split(">")[0].split("[")[0].lower() for d in deps_str.split(",")]
                for dep in deps:
                    if dep not in approved_runtime_deps:
                        pytest.fail(
                            f"UNAPPROVED RUNTIME DEPENDENCY: '{dep}'\n"
                            f"Add to approved list or remove from pyproject.toml."
                        )
