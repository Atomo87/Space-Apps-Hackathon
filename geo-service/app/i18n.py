import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

_english = json.loads(Path(__file__).with_name("en-US.json").read_text(encoding="utf-8"))
_use_english = ContextVar("geosafra_use_english", default=False)


@contextmanager
def analysis_locale(language: str | None):
    token = _use_english.set(isinstance(language, str) and language.lower().startswith("en"))
    try:
        yield
    finally:
        _use_english.reset(token)


def is_english() -> bool:
    return _use_english.get()


def tr(message: str | None, *values) -> str | None:
    if message is None:
        return None
    localized = _english.get(message, message) if is_english() else message
    return localized.format(*values) if values else localized


_TEXT_FIELDS = {
    "name", "dataset", "disclaimer", "source_note", "grid_note", "citation",
    "resolution", "relief_class", "driest", "wettest", "notes",
}
_SNAPSHOT_TEMPLATES = tuple(
    (re.compile(re.escape(message).replace(r"\{0\}", r"(\d+)")), english)
    for message, english in _english.items()
    if message.startswith(("Umidade dos primeiros ~5 cm", "Índice de estresse evaporativo (ET real ÷ potencial)"))
    and "{0}" in message
)


def _source_copy(value: str) -> str:
    for pattern, english in _SNAPSHOT_TEMPLATES:
        if match := pattern.fullmatch(value):
            return english.format(match[1])
    return tr(value)


def localize_metadata(value):
    """Render text from stored source snapshots without modifying their data or codes."""
    if not is_english():
        return value
    return _localize_value(value)


def _localize_value(value):
    if isinstance(value, dict):
        localized = {}
        for key, item in value.items():
            if key in _TEXT_FIELDS and isinstance(item, str):
                localized[key] = _source_copy(item)
            elif key == "notes" and isinstance(item, list):
                localized[key] = [_source_copy(note) if isinstance(note, str) else _localize_value(note) for note in item]
            else:
                localized[key] = _localize_value(item)
        return localized
    if isinstance(value, list):
        return [_localize_value(item) for item in value]
    return value
