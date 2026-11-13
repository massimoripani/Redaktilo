# -*- coding: utf-8 -*-
"""Konvertado cx ↔ ĉ (x-sistemo) en la elekto aŭ en la tuta teksto.

Etikedoj kaj la enhavo de <ret>…</ret> (retadresoj) ne estas tuŝataj.
"""
import re

CATEGORY = "Konvertiloj"

X_TO_ACCENT = {
    "Cx": "Ĉ", "cx": "ĉ", "CX": "Ĉ", "cX": "ĉ",
    "Gx": "Ĝ", "gx": "ĝ", "GX": "Ĝ", "gX": "ĝ",
    "Hx": "Ĥ", "hx": "ĥ", "HX": "Ĥ", "hX": "ĥ",
    "Jx": "Ĵ", "jx": "ĵ", "JX": "Ĵ", "jX": "ĵ",
    "Sx": "Ŝ", "sx": "ŝ", "SX": "Ŝ", "sX": "ŝ",
    "Ux": "Ŭ", "ux": "ŭ", "UX": "Ŭ", "uX": "ŭ",
}
ACCENT_TO_X = {"Ĉ": "Cx", "ĉ": "cx", "Ĝ": "Gx", "ĝ": "gx", "Ĥ": "Hx", "ĥ": "hx",
               "Ĵ": "Jx", "ĵ": "jx", "Ŝ": "Sx", "ŝ": "sx", "Ŭ": "Ux", "ŭ": "ux"}

_PROTECT = re.compile(r"(<ret>.*?</ret>|<[^>]*>)", re.DOTALL)


def _convert(text, regex, mapping):
    parts = _PROTECT.split(text)
    for i in range(0, len(parts), 2):          # solo il testo fuori da tag e <ret>
        parts[i] = regex.sub(lambda m: mapping[m.group(0)], parts[i])
    return "".join(parts)


_X_RE = re.compile("|".join(sorted(X_TO_ACCENT, key=len, reverse=True)))
_ACC_RE = re.compile("[" + "".join(ACCENT_TO_X) + "]")


def to_accents(text):
    return _convert(text, _X_RE, X_TO_ACCENT)


def to_x(text):
    return _convert(text, _ACC_RE, ACCENT_TO_X)


ACTIONS = [
    ("cx → ĉ", lambda ctx: ctx.apply(to_accents)),
    ("ĉ → cx", lambda ctx: ctx.apply(to_x)),
]
