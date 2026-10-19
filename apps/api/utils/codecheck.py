"""Clean up and validate Python code emitted by an LLM before it is written to disk."""
from __future__ import annotations

import ast
import re
from pathlib import PurePosixPath

_FENCE = re.compile(r"^\s*```[\w+-]*\s*$")
_SEPARATOR = re.compile(r"^\s*(-{3,}|={3,}|\*{3,})\s*$")


def sanitize_python(code: str) -> str:
    """Drop markdown fences and bare separator lines (``---``) that models put between blocks.

    Separator lines are only dropped when they are not inside a string literal, which we
    approximate by only removing lines that would make the module unparsable.
    """
    lines = [ln for ln in code.splitlines() if not _FENCE.match(ln)]
    cleaned = "\n".join(lines).strip("\n") + "\n"
    if syntax_error(cleaned) is None:
        return cleaned
    stripped = "\n".join(ln for ln in lines if not _SEPARATOR.match(ln)).strip("\n") + "\n"
    return stripped if syntax_error(stripped) is None else cleaned


def syntax_error(code: str) -> str | None:
    """Return a one-line description of the first syntax error, or None if the code parses."""
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return f"line {exc.lineno}: {exc.msg}"
    return None


def module_name(target_file: str) -> str:
    """'app/services/account_service.py' -> 'app.services.account_service'."""
    p = PurePosixPath(target_file.replace("\\", "/"))
    return ".".join(p.with_suffix("").parts)


def missing_local_imports(code: str, known_modules: set[str]) -> list[str]:
    """Imports that look project-local (share a top-level package with known modules)
    but point to a module that the migration does not generate."""
    tops = {m.split(".")[0] for m in known_modules}
    missing: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return missing
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        for n in names:
            if n.split(".")[0] in tops and n not in known_modules and not any(
                k.startswith(n + ".") for k in known_modules
            ):
                missing.append(n)
    return sorted(set(missing))


def undefined_names(code: str) -> list[str]:
    """Names that are read somewhere but never bound anywhere in the file (and are not
    builtins). Deliberately loose (ignores scope), so it only flags clear misses such as a
    test that uses `Account` without importing it."""
    import builtins

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    bound: set[str] = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            (used if isinstance(node.ctx, ast.Load) else bound).add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                bound.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)
        elif isinstance(node, ast.MatchAs) and node.name:
            bound.add(node.name)
    return sorted(used - bound)


def _write_tree(root, files: dict[str, str]) -> None:
    from pathlib import Path

    root = Path(root)
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        for d in p.relative_to(root).parents:
            init = root / d / "__init__.py"
            if str(d) != "." and not init.exists():
                init.write_text("")


def import_errors(modules: dict[str, str], timeout: int = 60) -> dict[str, str]:
    """Import each generated module in a clean subprocess. Returns {target_file: last error line}."""
    import os
    import subprocess
    import sys
    import tempfile

    errors: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        _write_tree(tmp, modules)
        for target in modules:
            r = subprocess.run(
                [sys.executable, "-c", f"import {module_name(target)}"],
                cwd=tmp, capture_output=True, text=True, timeout=timeout,
                env={**os.environ, "PYTHONPATH": tmp},
            )
            if r.returncode != 0:
                lines = [ln for ln in r.stderr.strip().splitlines() if ln.strip()]
                errors[target] = lines[-1] if lines else "import failed"
    return errors


def run_tests(modules: dict[str, str], tests: dict[str, str], timeout: int = 300) -> dict:
    """Run generated pytest files against generated modules in a temp dir.

    Returns counts plus the collection errors (ImportError / NameError / SyntaxError at
    import time). Assertion failures are reported as counts only: feeding them back to the
    test writer would teach it to bend assertions toward the migrated code, which defeats
    equivalence testing.
    """
    import os
    import re as _re
    import subprocess
    import sys
    import tempfile

    files = dict(modules)
    files.update({f"tests_generated/{name}": code for name, code in tests.items()})
    with tempfile.TemporaryDirectory() as tmp:
        _write_tree(tmp, files)
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--tb=line",
             "--rootdir", tmp, "tests_generated"],
            cwd=tmp, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "PYTHONPATH": tmp},
        )
    out = r.stdout
    summary = out.strip().splitlines()[-1] if out.strip() else ""
    counts = {k: int(m.group(1)) for k in ("passed", "failed", "errors", "error")
              if (m := _re.search(rf"(\d+) {k}\b", summary))}
    collection = sorted(set(_re.findall(r"^E\s+((?:ImportError|ModuleNotFoundError|NameError|SyntaxError|AttributeError)[^\n]*)", out, _re.M)))
    return {
        "summary": summary,
        "passed": counts.get("passed", 0),
        "failed": counts.get("failed", 0),
        "errors": counts.get("errors", counts.get("error", 0)),
        "collection_errors": collection[:10],
        "tail": out[-2500:],
    }
