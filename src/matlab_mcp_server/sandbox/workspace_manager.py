import shutil
from pathlib import Path


class WorkspaceManager:
    def __init__(self, sandbox_dir: Path, shadow_dir: Path | None = None):
        self.sandbox_dir = sandbox_dir
        self.shadow_dir = shadow_dir or (
            Path(__file__).parent / "matlab_shadows"
        )

    def ensure_sandbox_exists(self) -> Path:
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        figures_dir = self.sandbox_dir / "figures"
        figures_dir.mkdir(exist_ok=True)
        data_dir = self.sandbox_dir / "data"
        data_dir.mkdir(exist_ok=True)
        return self.sandbox_dir

    def cleanup_residual_files(self) -> dict:
        report = {"lock_files_cleaned": 0, "cache_files_cleaned": 0, "other_cleaned": 0}
        patterns = {
            "lock_files": "*.lck",
            "cache_files": "*.slxc",
            "other": "*.autosave",
        }
        for category, pattern in patterns.items():
            for f in self.sandbox_dir.rglob(pattern):
                try:
                    f.unlink()
                    report[f"{category}_cleaned"] = report.get(f"{category}_cleaned", 0) + 1
                except OSError:
                    pass
        return report

    def get_shadow_dir_path(self) -> str:
        return str(self.shadow_dir.resolve())

    def reset_workspace(self) -> dict:
        self.cleanup_residual_files()
        figures_dir = self.sandbox_dir / "figures"
        for f in figures_dir.iterdir():
            if f.is_file():
                f.unlink()
        return {"status": "reset", "sandbox_dir": str(self.sandbox_dir)}
