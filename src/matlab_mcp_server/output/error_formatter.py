import traceback


def format_error(exc: Exception) -> dict:
    return {
        "success": False,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": traceback.format_exc(),
    }
