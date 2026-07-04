"""Unit tests for the pure echo service (src/services/echo.py).

Pins AC-6, AC-7, AC-8. Observes only the locked entry point
`src.services.echo:echo`. No web layer, no I/O.
"""
from src.services.echo import echo


def test_echo_prefixes_message():
    # AC-6: non-empty message is returned with the literal "Echo: " prefix.
    assert echo("hello") == "Echo: hello"


def test_echo_empty_message():
    # AC-7: empty string is valid and echoes as just the prefix.
    assert echo("") == "Echo: "


def test_echo_is_verbatim():
    # AC-8: message is echoed verbatim after the prefix — no trimming,
    # no HTML-escaping, no mangling of non-ASCII or markup characters.
    msg = "  Héllo 🎉 <b>tag</b>  "
    assert echo(msg) == "Echo: " + msg
