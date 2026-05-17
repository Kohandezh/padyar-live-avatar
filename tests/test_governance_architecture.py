"""Architecture layering tests — verify clean separation between runtime layers.

WHY:  Ensures the adapter/scheduler/api layers stay decoupled. If scheduler imports
      engine internals directly, the replaceable-engine strategy breaks.
RISK:  Layering violations make it impossible to swap the engine without rewriting
      the runtime. This is the core architectural contract.
"""

import ast
import importlib
from abc import ABC
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "padyar_live"


# --- Adapter contract ---

def test_engine_adapter_is_abstract():
    """EngineAdapter must remain abstract — cannot be instantiated."""
    from padyar_live.adapters.engine import EngineAdapter
    assert issubclass(EngineAdapter, ABC)
    with pytest.raises(TypeError):
        EngineAdapter()


def test_engine_adapter_has_exactly_two_methods():
    """EngineAdapter contract is minimal: generate_frames + health_check.

    Adding methods to this interface should be a deliberate decision,
    not an accident. This test forces awareness.
    """
    from padyar_live.adapters.engine import EngineAdapter

    abstract_methods = set(EngineAdapter.__abstractmethods__)
    expected = {"generate_frames", "health_check"}
    assert abstract_methods == expected, (
        f"EngineAdapter abstract methods changed: {abstract_methods}\n"
        f"Expected: {expected}\n"
        f"If intentional, update this test."
    )


def test_fake_engine_is_only_concrete_adapter():
    """Only FakeEngineAdapter should exist in the adapters module."""
    import padyar_live.adapters.engine as engine_mod
    from padyar_live.adapters.engine import EngineAdapter

    adapters = [
        obj for name, obj in vars(engine_mod).items()
        if isinstance(obj, type) and issubclass(obj, EngineAdapter) and obj is not EngineAdapter
    ]
    names = {a.__name__ for a in adapters}
    assert names == {"FakeEngineAdapter"}, (
        f"Unexpected adapter classes found: {names - {'FakeEngineAdapter'}}\n"
        f"Real engine adapters should live in a separate module."
    )


# --- Layer dependency rules ---

def _get_imports(filepath: Path) -> set[str]:
    """Extract top-level imports from a file."""
    tree = ast.parse(filepath.read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


def test_scheduler_does_not_import_engine_internals():
    """scheduler/ must only use the EngineAdapter interface, never engine internals."""
    scheduler_dir = SRC_DIR / "scheduler"
    for f in scheduler_dir.rglob("*.py"):
        imports = _get_imports(f)
        # Must import from adapter, not from any engine implementation
        if "padyar_live" in imports or any("padyar_live" in i for i in imports):
            source = f.read_text()
            # Must use adapters.engine, not any internal module
            assert "from padyar_live.adapters.engine import EngineAdapter" in source or \
                   "from padyar_live.adapters import engine" in source or \
                   "padyar_live.adapters.engine" in source, \
                f"{f.name} imports from padyar_live but doesn't use the adapter interface"


def test_api_does_not_import_scheduler_internals():
    """api/ must use scheduler through FrameScheduler, not internal queue/state."""
    api_dir = SRC_DIR / "api"
    for f in api_dir.rglob("*.py"):
        source = f.read_text()
        # API must not reach into scheduler internals
        assert "_output_queue" not in source, \
            f"{f.name}: API layer must not access scheduler._output_queue directly"
        assert "_lock" not in source, \
            f"{f.name}: API layer must not access scheduler._lock directly"


def test_ws_handler_only_depends_on_adapter_contract():
    """WS handler must depend on FrameScheduler (which uses adapter), not on engine."""
    ws_file = SRC_DIR / "api" / "ws.py"
    source = ws_file.read_text()

    # Must import FrameScheduler
    assert "FrameScheduler" in source
    # Must NOT import engine directly (type hints in TYPE_CHECKING are ok)
    assert "FakeEngineAdapter" not in source, \
        "ws.py must not reference FakeEngineAdapter — testing concern"

    # Must NOT import FakeEngineAdapter
    assert "FakeEngineAdapter" not in source, \
        "ws.py must not reference FakeEngineAdapter — that's a testing concern"


def test_models_module_has_no_runtime_imports():
    """models/schemas.py must not depend on runtime, scheduler, or adapters."""
    models_file = SRC_DIR / "models" / "schemas.py"
    source = models_file.read_text()

    assert "padyar_live.runtime" not in source, \
        "models must not import from runtime"
    assert "padyar_live.scheduler" not in source, \
        "models must not import from scheduler"
    assert "padyar_live.adapters" not in source, \
        "models must not import from adapters"


def test_no_circular_imports_between_layers():
    """Verify module can be imported without circular import errors."""
    modules = [
        "padyar_live.models.schemas",
        "padyar_live.runtime.config",
        "padyar_live.runtime.latency",
        "padyar_live.adapters.engine",
        "padyar_live.scheduler.frame_scheduler",
        "padyar_live.runtime.session_manager",
    ]
    for mod_name in modules:
        mod = importlib.import_module(mod_name)
        assert mod is not None, f"Failed to import {mod_name}"
