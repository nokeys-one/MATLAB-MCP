from dataclasses import dataclass
from .whitelist import L3_BLOCKED_FUNCTIONS


@dataclass
class InjectionRisk:
    keyword: str
    severity: str
    line: int
    context: str
    reason: str


MATLAB_REGEX_DANGEROUS_CALLS = {
    "eval", "evalc", "evalin", "feval", "builtin", "str2func",
    "system", "dos", "unix",
    "delete", "rmdir", "movefile", "copyfile",
    "fopen", "fwrite", "fclose",
    "addpath", "rmpath", "cd",
    "urlread", "urlwrite", "webread", "webwrite",
    "java", "actxserver",
    "setenv", "getenv",
    "keyboard",
}

STRING_CONCAT_PATTERNS = [
    r"\[[\s']*sy[\s']*[\s']*stem[\s']*[\s']*\]",
    r"\[[\s']*ev[\s']*[\s']*al[\s']*[\s']*\]",
    r"\[[\s']*fe[\s']*[\s']*val[\s']*[\s']*\]",
    r"strcat\s*\(\s*['\"]sy",
    r"strcat\s*\(\s*['\"]ev",
]


def _is_inside_string(line: str, pos: int) -> bool:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if i >= pos:
            break
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
    return in_single or in_double


def analyze_matlab_code(code: str) -> list[InjectionRisk]:
    import re
    risks: list[InjectionRisk] = []
    lines = code.split("\n")

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("%") or stripped.startswith("#"):
            continue

        for keyword in MATLAB_REGEX_DANGEROUS_CALLS:
            pattern = rf'\b{re.escape(keyword)}\s*\('
            for match in re.finditer(pattern, line):
                pos = match.start()
                if not _is_inside_string(line, pos):
                    severity = "block" if keyword in L3_BLOCKED_FUNCTIONS else "warn"
                    risks.append(InjectionRisk(
                        keyword=keyword,
                        severity=severity,
                        line=line_num,
                        context=stripped[:200],
                        reason=f"Dangerous call '{keyword}()' detected at line {line_num}",
                    ))

        for pattern in STRING_CONCAT_PATTERNS:
            for match in re.finditer(pattern, line):
                risks.append(InjectionRisk(
                    keyword="string_concat_evasion",
                    severity="block",
                    line=line_num,
                    context=stripped[:200],
                    reason=f"String concatenation evasion pattern detected: {match.group()}",
                ))

    return risks


def is_code_safe(code: str) -> tuple[bool, list[InjectionRisk]]:
    risks = analyze_matlab_code(code)
    blocking = [r for r in risks if r.severity == "block"]
    return len(blocking) == 0, risks
