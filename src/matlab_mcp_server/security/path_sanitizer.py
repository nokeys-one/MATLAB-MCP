import os
from pathlib import Path


class PathTraversalError(Exception):
    pass


def sanitize_path(file_path: str, sandbox_dir: str) -> str:
    if not file_path or not file_path.strip():
        raise PathTraversalError("Empty file path")

    sandbox_real = os.path.realpath(sandbox_dir)
    normalized = os.path.normpath(file_path)
    full_path = os.path.realpath(os.path.join(sandbox_real, normalized))

    if not full_path.startswith(sandbox_real + os.sep) and full_path != sandbox_real:
        raise PathTraversalError(
            f"Path traversal detected: '{file_path}' resolves outside sandbox"
        )

    return full_path
