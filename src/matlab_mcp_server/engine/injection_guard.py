from ..security.injection_detector import is_code_safe


class InjectionBlockedError(Exception):
    def __init__(self, risks: list):
        self.risks = risks
        keywords = ", ".join(r.keyword for r in risks)
        super().__init__(f"Code blocked by injection guard: {keywords}")


def pre_execute_check(code: str):
    safe, risks = is_code_safe(code)
    if not safe:
        blocked = [r for r in risks if r.severity == "block"]
        raise InjectionBlockedError(blocked)
