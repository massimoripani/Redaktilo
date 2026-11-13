# -*- coding: utf-8 -*-
"""Funzioni condivise dai plugin (convenzioni Monato)."""
import os
import re
import sys

# Cartella unica dei vocabolari (accanto al programma, non accanto ai plugin):
#   vortaroj/propra.txt, vortaroj/vortaro_komoj.txt, vortaroj/html_entoj.txt, vortaroj/eo/...
# Con l'exe (PyInstaller) è accanto a Redaktilo.exe, altrimenti accanto a editor.py.
_BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
    else os.path.dirname(os.path.abspath(__file__))
VORTARO_DIR = os.path.join(_BASE, "vortaroj")


def vortaro_path(*parts):
    """Percorso di un file di vocabolario: vortaro_path('vortaro_komoj.txt')."""
    return os.path.join(VORTARO_DIR, *parts)

# Tag previsti dalle convenzioni Monato
SELF_CLOSING = {"hs", "nl", "ss", "mend"}
KNOWN_TAGS = {
    "art", "aut", "bib", "bibaut", "bibt", "c", "d", "foto", "hs", "inf", "it",
    "k", "kod", "land", "lin", "mm", "n-ro", "nl", "noto", "p", "prez", "r",
    "ret", "rub", "sinp", "ss", "sub", "sup", "sv", "t", "tab", "td", "tt",
    "cit", "lig", "loko", "mend", "retfoto",
}

TAG_RE = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9\-]*)([^>]*?)(/?)>")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def blank_comments(text):
    """Sostituisce i commenti <!-- --> con spazi, mantenendo righe e colonne."""
    return COMMENT_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


# ---------------------------------------------------------------- validazione
def validate_tags(text):
    """Ritorna una lista di (riga, messaggio)."""
    clean = blank_comments(text)
    errors = []
    stack = []          # (tag, riga)
    last_end = 0

    def check_loose_text(start, end):
        # Dentro <art> non può esserci testo "libero" (solo dentro altri tag)
        if stack and stack[-1][0] == "art":
            chunk = clean[start:end]
            m = re.search(r"\S", chunk)
            if m:
                errors.append((line_of(clean, start + m.start()),
                               "Teksto ekster etikedo ene de <art> (ĝi devas esti en <p>, <tt>, ktp.)"))

    for m in TAG_RE.finditer(clean):
        check_loose_text(last_end, m.start())
        last_end = m.end()
        closing, name, _attrs, selfslash = m.groups()
        line = line_of(clean, m.start())

        if name not in KNOWN_TAGS and not closing:
            errors.append((line, f"Etikedo ne antaŭvidita de la konvencioj: <{name}>"))

        if name in SELF_CLOSING or selfslash:
            if closing:
                errors.append((line, f"Senbezona fermo </{name}> (malplena etikedo)"))
            continue

        if not closing:
            stack.append((name, line))
            continue

        # chiusura
        idx = None
        for i in range(len(stack) - 1, -1, -1):
            if stack[i][0] == name:
                idx = i
                break
        if idx is None:
            errors.append((line, f"Fermo sen malfermo: </{name}>"))
            continue
        # tag rimasti aperti sopra quello che si sta chiudendo
        for t, l in stack[idx + 1:]:
            errors.append((l, f"<{t}> ne fermita (antaŭ </{name}> en linio {line})"))
        del stack[idx:]

    for t, l in stack:
        errors.append((l, f"Mankas ferma etikedo: <{t}> neniam fermiĝas"))

    errors.sort(key=lambda e: e[0])
    return errors


def validate_comments(text):
    """Controlla che <!-- e --> siano bilanciati e non annidati."""
    errors = []
    inside = False
    start_line = None
    for line_num, line in enumerate(text.split("\n"), start=1):
        pos = 0
        while pos < len(line):
            if line.startswith("<!--", pos):
                if inside:
                    errors.append((line_num, "Entenita komento (<!-- ene de komento)"))
                inside, start_line = True, line_num
                pos += 4
                continue
            if line.startswith("-->", pos):
                if not inside:
                    errors.append((line_num, "Fermo de komento sen malfermo (-->)"))
                inside, start_line = False, None
                pos += 3
                continue
            pos += 1
    if inside:
        errors.append((start_line, "Nefermita komento (<!-- sen -->)"))
    return errors


# ------------------------------------------------------- parole con maiuscola
_KW_RE = re.compile(
    r"\b[A-Z][a-zA-ZĈ-ŭ'\-]*(?:[^\S\n]*[A-Z][a-zA-ZĈ-ŭ'\-]*)*\b")

_SKIP_BLOCKS = re.compile(r"<(sv|inf|kod|n-ro|aut|land|rub)>.*?</\1>", re.DOTALL)


def estrai_parole(text):
    """Parole/nomi che iniziano con maiuscola (come nei tuoi script),
    senza commenti, tag e blocchi di servizio."""
    t = COMMENT_RE.sub("", text)
    t = _SKIP_BLOCKS.sub(" ", t)
    t = re.sub(r"<[^>]*>", " ", t)
    t = re.sub(r"&[A-Za-z0-9#]+;", " ", t)      # entità (&Uuml; ecc.)
    return _KW_RE.findall(t)
