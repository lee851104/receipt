"""Checks on text people type, shared by the request bodies."""
import unicodedata


def visible(text, field):
    """text itself, or a ValueError (so a 422 answer) when it holds a control, invisible, private, unassigned or
    line-breaking character, any of which could make it look blank, break a line or pass for something else."""
    if any(unicodedata.category(char)[0] == "C" or unicodedata.category(char) in ("Zl", "Zp") for char in text):
        raise ValueError(f"{field} holds a control, invisible or line-breaking character")
    return text
