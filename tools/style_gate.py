"""AST-гейт стиля кода: один выход, 1-2 оператора в теле, без while/break/continue.

Правила проекта проверяются не глазами ревьюера, а этим скриптом в pre-commit и CI:
    python tools/style_gate.py .
"""

import ast
import sys
from pathlib import Path

MAX_STATEMENTS = 2
FORBIDDEN = (ast.While, ast.Break, ast.Continue)
SKIP_DIRS = {
    ".venv",
    "__pycache__",
    ".git",
    ".ruff_cache",
    ".pytest_cache",
    "artifacts",
    ".local_s3",
}


def is_docstring(node: ast.stmt) -> bool:
    """Отделяет докстринг от исполняемых операторов."""
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def body_of(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    """Исполняемое тело функции без докстринга."""
    return [stmt for stmt in fn.body if not is_docstring(stmt)]


def returns_of(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Return]:
    """Все return внутри функции, включая ветки условий и циклов."""
    return [node for node in ast.walk(fn) if isinstance(node, ast.Return)]


def has_forbidden(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Ловит while, break и continue на любой глубине."""
    return any(isinstance(node, FORBIDDEN) for node in ast.walk(fn))


def closing_return(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.Return | None:
    """Последний return функции либо None, если его нет."""
    found = returns_of(fn)
    return found[-1] if found else None


def closes_body(fn: ast.FunctionDef | ast.AsyncFunctionDef, ret: ast.Return | None) -> bool:
    """Проверяет, что return является последним оператором тела."""
    body = body_of(fn)
    return bool(body) and ret is not None and body[-1] is ret


def violations_of(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Список нарушений стиля для одной функции."""
    checks = {
        "больше 2 исполняемых операторов": len(body_of(fn)) > MAX_STATEMENTS,
        "while/break/continue запрещены": has_forbidden(fn),
        "нужен ровно один return": len(returns_of(fn)) != 1,
        "return обязан замыкать тело": not closes_body(fn, closing_return(fn)),
    }
    return [message for message, broken in checks.items() if broken]


def functions_of(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Все объявления функций модуля, включая вложенные и методы."""
    return [
        node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def check_file(path: Path) -> list[str]:
    """Нарушения стиля в одном файле."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        f"{path}:{fn.lineno} {fn.name}: {message}"
        for fn in functions_of(tree)
        for message in violations_of(fn)
    ]


def python_files(root: Path) -> list[Path]:
    """Файлы .py под корнем, кроме служебных каталогов и тестов."""
    return sorted(
        path
        for path in root.rglob("*.py")
        if not SKIP_DIRS.intersection(path.parts) and not path.name.startswith("test_")
    )


def collect(root: str) -> list[str]:
    """Нарушения по всему дереву."""
    return [problem for path in python_files(Path(root)) for problem in check_file(path)]


def report(problems: list[str]) -> int:
    """Печатает отчёт и возвращает код выхода."""
    print("\n".join(problems) if problems else "style-gate: OK")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    """Точка входа CLI."""
    return report(collect(argv[1] if len(argv) > 1 else "."))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
