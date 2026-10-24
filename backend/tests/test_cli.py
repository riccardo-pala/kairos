import sys

import pytest

from kairos.__main__ import main


@pytest.mark.parametrize("language,expected_title,expected_intro", [
    ("it", "Visita medica", "risposte predefinite"),
    ("en", "Medical appointment", "scripted responses"),
])
def test_demo_uses_selected_language_without_contacting_a_model(
    monkeypatch, capsys, language, expected_title, expected_intro
):
    monkeypatch.setattr(sys, "argv", ["kairos", "--language", language])
    main()
    output = capsys.readouterr().out
    assert expected_intro in output
    assert expected_title in output
    assert '"ready_for_review"' in output
    assert '"it":' in output and '"en":' in output
