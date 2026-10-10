from pytest_run_context import RunContext, get_run_context


def test_standalone_context(run_context: RunContext) -> None:
    assert run_context is get_run_context()
    assert run_context.custom.lifecycle_event == "started"

    run_context.custom.message = "tested"
    run_context.save()

    assert run_context.custom.message == "tested"
