from pytest_run_context import RunContext, get_run_context


def test_share_and_save_sqlite_context(run_context: RunContext) -> None:
    assert get_run_context() is run_context
    assert run_context.custom.lifecycle_event == "started"

    run_context.custom.message = "saved in SQLite"
    run_context.save()

    assert run_context.custom.message == "saved in SQLite"
