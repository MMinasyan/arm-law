"""Run with python3 -B test_act.py; no network requests."""
import contextlib
import os
import tempfile
from pathlib import Path
from unittest import mock

from arlis.act import get_act

url = "https://www.arlis.am/hy/acts/1/latest"
body = "# Act\nText.\n"
metadata = {
    "title": "Փորձ",
    "changes": {"change_history": [], "changed_acts": []},
    "relations": {
        "general_relations": [], "judicial_precedents": [],
        "official_clarifications": [], "anti_constitutional": [],
    },
}

_RELATIVE_DATA = "relative-data"


@contextlib.contextmanager
def plugin_data(value):
    """Run with PLUGIN_DATA set to value, or removed when value is None."""
    with mock.patch.dict(os.environ):
        if value is None:
            os.environ.pop("PLUGIN_DATA", None)
        else:
            os.environ["PLUGIN_DATA"] = value
        yield


def check():
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir).resolve()
        cwd_dir, data_dir, override_dir = (
            root / "cwd", root / "data", root / "override",
        )
        for directory in (cwd_dir, data_dir, override_dir):
            directory.mkdir()
        with contextlib.chdir(cwd_dir):
            cwd = Path.cwd()

            def expect_saved(plugin_value, output_dir, destination):
                """Successful row: real formatter and writer, exact saved file."""
                with mock.patch(
                    "arlis.act._read_act", return_value=(metadata, body)
                ) as read_act:
                    with plugin_data(plugin_value):
                        result = get_act(url, output_dir)
                read_act.assert_called_once_with(url)
                target = destination / "1.md"
                assert result.splitlines()[0] == f"Saved: {target}"
                assert target.is_absolute() and target.is_file()
                with open(target, encoding="utf-8") as handle:
                    assert handle.read().endswith(body)

            # PLUGIN_DATA absent, then empty: standalone cwd behavior.
            expect_saved(None, None, cwd / ".arlis")
            expect_saved("", None, cwd / ".arlis")
            # PLUGIN_DATA absent with explicit relative and empty output_dir.
            expect_saved(None, "acts", cwd / "acts")
            expect_saved(None, "", cwd)
            # Absolute PLUGIN_DATA: relative output_dir values join it.
            expect_saved(str(data_dir), None, data_dir / ".arlis")
            expect_saved(str(data_dir), "acts", data_dir / "acts")
            expect_saved(str(data_dir), "", data_dir)
            # Absolute output_dir: PLUGIN_DATA is never consulted.
            expect_saved(_RELATIVE_DATA, str(override_dir), override_dir)
            expect_saved(str(data_dir), str(override_dir), override_dir)

            # A relative PLUGIN_DATA is rejected before any read or write.
            with mock.patch(
                "arlis.act._read_act", return_value=(metadata, body)
            ) as read_act:
                with plugin_data(_RELATIVE_DATA):
                    for output_dir in (None, "acts"):
                        try:
                            get_act(url, output_dir)
                        except ValueError as error:
                            assert str(error) == (
                                "PLUGIN_DATA must be an absolute directory path"
                            )
                        else:
                            raise AssertionError("accepted a relative PLUGIN_DATA")
                read_act.assert_not_called()
            assert not (cwd / _RELATIVE_DATA).exists()

            # URL validation wins over an invalid PLUGIN_DATA setting.
            with mock.patch("arlis.act._read_act") as read_act:
                with plugin_data(_RELATIVE_DATA):
                    try:
                        get_act("անվավեր")
                    except ValueError as error:
                        assert str(error).startswith("not a valid arlis act URL:")
                    else:
                        raise AssertionError("accepted an invalid act URL")
                read_act.assert_not_called()

            # Windows-special output_dir forms with mocked Path.mkdir and
            # _save, so no platform writes outside the temporary sandbox:
            # a root-anchored value, a same-drive relative value and a
            # different-drive value.
            drive = Path.cwd().drive
            for output_dir in (
                "\\acts",
                drive + "acts",
                "Z:acts" if drive != "Z:" else "Y:acts",
            ):
                with (
                    mock.patch(
                        "arlis.act._read_act", return_value=(metadata, body)
                    ) as read_act,
                    mock.patch.object(Path, "mkdir"),
                    mock.patch("arlis.act._save") as save,
                ):
                    with plugin_data(None):
                        result = get_act(url, output_dir)
                read_act.assert_called_once_with(url)
                save.assert_called_once()
                captured = save.call_args.args[0]
                assert captured.is_absolute()
                assert result.splitlines()[0] == f"Saved: {captured}"
                assert captured == Path(os.path.abspath(output_dir)) / "1.md"

    print(
        "PASS: PLUGIN_DATA and output_dir destinations, validation order, "
        "Windows path forms"
    )


if __name__ == "__main__":
    check()