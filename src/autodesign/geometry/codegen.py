"""LLM 코드생성(방식 B) 안전 실행 — AST 화이트리스트 + 서브프로세스 샌드박스.

원칙(docs/06 §5): LLM이 생성한 FreeCAD Python은 절대 직접 exec 하지 않는다.
1) AST로 import/위험호출을 화이트리스트 검사 → 위반 시 거부.
2) 통과분만 freecadcmd 서브프로세스에서 실행(리소스/시간 제한). 미설치 시 분석만.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import List

ALLOWED_IMPORTS = {"FreeCAD", "Part", "math", "Draft", "Mesh"}
FORBIDDEN_NAMES = {
    "os", "sys", "subprocess", "shutil", "socket", "open", "eval", "exec",
    "compile", "__import__", "input", "globals", "locals", "vars", "getattr",
    "setattr", "delattr", "importlib", "pickle", "marshal", "ctypes",
}
FORBIDDEN_ATTRS = {"system", "popen", "remove", "rmtree", "unlink", "spawn"}


@dataclass
class SafetyReport:
    safe: bool
    violations: List[str] = field(default_factory=list)


def check_script(code: str) -> SafetyReport:
    """생성 스크립트의 정적 안전성 검사."""
    violations: List[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return SafetyReport(False, [f"구문 오류: {e}"])

    for node in ast.walk(tree):
        # import 화이트리스트
        if isinstance(node, ast.Import):
            for n in node.names:
                root = n.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    violations.append(f"금지 import: {n.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS:
                violations.append(f"금지 from-import: {node.module}")
        # 위험 이름 호출/참조
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            violations.append(f"금지 식별자: {node.id}")
        # 위험 속성 접근 (os.system 등)
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
            violations.append(f"금지 속성: .{node.attr}")
        # 던더 접근 차단
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            violations.append(f"던더 속성 접근: .{node.attr}")

    return SafetyReport(len(violations) == 0, violations)


def run_in_sandbox(code: str, out_step: str = "part.step", timeout: float = 60.0) -> dict:
    """안전성 통과 후 freecadcmd 서브프로세스에서 실행.

    반환: {status, ...}. FreeCAD 미설치 시 status='freecad_unavailable'.
    """
    report = check_script(code)
    if not report.safe:
        return {"status": "rejected", "violations": report.violations}

    import shutil
    import subprocess  # 샌드박스 실행에만 국한 사용

    binary = shutil.which("freecadcmd") or shutil.which("FreeCADCmd")
    if not binary:
        return {"status": "freecad_unavailable",
                "note": "AST 안전성 통과. freecadcmd 설치 시 실행됩니다."}

    wrapper = (
        code
        + "\n\n# --- 자동 export ---\n"
        + f"try:\n    shape.exportStep({out_step!r})\n    print('STEP_OK')\n"
          "except Exception as _e:\n    print('EXPORT_FAIL', _e)\n"
    )
    try:
        proc = subprocess.run([binary, "-c", wrapper], capture_output=True,
                              text=True, timeout=timeout)
        ok = "STEP_OK" in proc.stdout
        return {"status": "ok" if ok else "exec_failed",
                "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:],
                "step": out_step if ok else None}
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
