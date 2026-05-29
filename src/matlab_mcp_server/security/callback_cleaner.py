from dataclasses import dataclass, field


LIFECYCLE_CALLBACKS = [
    "PreLoadFcn", "PostLoadFcn", "PreSaveFcn", "PostSaveFcn",
    "CloseFcn", "InitFcn", "StartFcn", "PauseFcn",
    "ContinueFcn", "StopFcn", "PreCopyFcn", "PostCopyFcn",
    "DeleteFcn", "ModelCloseFcn", "CloseInitFcn",
]

BLOCK_CALLBACKS = [
    "ClickFcn", "DeleteFcn", "CopyFcn", "MoveFcn",
    "NameChangeFcn", "ParentCloseFcn", "OpenFcn", "CloseFcn",
    "PostSaveFcn", "PreSaveFcn", "ClipboardFcn", "DestroyFcn",
]


@dataclass
class CleanupReport:
    stripped_callbacks: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    success: bool = True


def build_sanitization_script(model_name: str) -> str:
    lines = [
        f"report = struct('stripped', {{}}, 'warnings', {{}});",
        f"try",
    ]
    for cb in LIFECYCLE_CALLBACKS:
        lines.append(f"  val = get_param('{model_name}', '{cb}');")
        lines.append(f"  if ~isempty(strtrim(val))")
        lines.append(f"    report.stripped{{end+1}} = struct('name','{cb}','value',val);")
        lines.append(f"    set_param('{model_name}', '{cb}', '');")
        lines.append(f"  end")
    lines.append(f"catch e")
    lines.append(f"  report.warnings{{end+1}} = e.message;")
    lines.append(f"end")
    return "\n".join(lines)
