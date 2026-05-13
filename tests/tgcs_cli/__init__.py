def load_tgcs_module(testcase):
    try:
        from scripts import tgcs
    except ModuleNotFoundError as exc:
        testcase.fail(f"scripts.tgcs should exist: {exc}")
    return tgcs
