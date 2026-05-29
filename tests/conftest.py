import pytest
from pathlib import Path


@pytest.fixture
def sandbox_dir(tmp_path):
    sandbox = tmp_path / "test_sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)
    return sandbox


@pytest.fixture
def shadow_dir(sandbox_dir):
    shadows = sandbox_dir / "shadows"
    shadows.mkdir(parents=True, exist_ok=True)
    return shadows
