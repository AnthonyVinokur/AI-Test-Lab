from src.cli.exit_codes import CliExitCode


def test_cli_exit_code_contract() -> None:
    assert CliExitCode.SUCCESS == 0
    assert CliExitCode.FAILURE == 1
    assert CliExitCode.INPUT_ERROR == 2
    assert CliExitCode.INFRASTRUCTURE_ERROR == 3

def test_cli_exit_codes_are_integer_compatible() -> None:
    assert isinstance(CliExitCode.SUCCESS, int)
    assert isinstance(CliExitCode.FAILURE, int)
    assert isinstance(CliExitCode.INPUT_ERROR, int)
    assert isinstance(CliExitCode.INFRASTRUCTURE_ERROR, int)
