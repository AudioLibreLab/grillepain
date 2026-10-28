import pytest


def test_help_runs(capsys):
    from grillepain.cli import main
    with pytest.raises(SystemExit) as e:
        main(["--help"])
    assert e.value.code == 0
    assert "analyse" in capsys.readouterr().out
