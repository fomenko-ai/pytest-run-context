from pytest_run_context import RunContext, get_run_context


def test_prepared_environment(run_context: RunContext) -> None:
    assert run_context is get_run_context()
    assert run_context.custom.environment == "prepared"

    run_context.custom.tests_completed = True
    run_context.save()
