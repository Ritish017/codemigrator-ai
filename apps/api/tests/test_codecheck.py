from utils.codecheck import missing_local_imports, module_name, sanitize_python, syntax_error


def test_strips_separator_between_classes():
    code = "class A:\n    pass\n\n\n---\n\nclass B:\n    pass\n"
    out = sanitize_python(code)
    assert syntax_error(out) is None
    assert "---" not in out


def test_strips_fences():
    out = sanitize_python("```python\nx = 1\n```\n")
    assert out == "x = 1\n"


def test_keeps_separator_inside_string():
    code = 's = """\n---\n"""\n'
    assert sanitize_python(code) == code


def test_module_name():
    assert module_name("app/services/account_service.py") == "app.services.account_service"


def test_missing_local_imports():
    code = "from app.core.database import x\nfrom app.services.account import y\nimport decimal\n"
    assert missing_local_imports(code, {"app.services.account"}) == ["app.core.database"]


def test_undefined_names():
    from utils.codecheck import undefined_names

    code = "from account import Repo\n\ndef test_x(tmp_path):\n    a = Account(1)\n    r = Repo()\n    assert len([i for i in range(3)]) == 3\n"
    assert undefined_names(code) == ["Account"]


def test_import_errors_and_run_tests():
    from utils.codecheck import import_errors, run_tests

    mods = {"bank/account.py": "def add(a, b):\n    return a + b\n",
            "bank/broken.py": "from collections import bisect\n"}
    errs = import_errors(mods)
    assert list(errs) == ["bank/broken.py"]

    res = run_tests({"bank/account.py": mods["bank/account.py"]},
                    {"test_a.py": "from bank.account import add\n\ndef test_ok():\n    assert add(1, 2) == 3\n\ndef test_bad():\n    assert add(1, 1) == 3\n"})
    assert res["passed"] == 1 and res["failed"] == 1 and res["collection_errors"] == []
