# -*- coding: utf-8 -*-
"""Restarigas alineojn en tekstoj rompitaj en mallongajn liniojn (el noveligo.py).

Agas sur la elekto, aŭ sur la tuta teksto se nenio estas elektita.
"""
import re

CATEGORY = "Aliaj iloj"
NAME = "Rekonstruilo de alineoj (rompita teksto)"


def rekonstrui_paragrafojn(teksto):
    teksto = teksto.replace("\r\n", "\n")
    teksto = re.sub(r"-\n", "", teksto)                    # trattino a fine riga
    teksto = re.sub(r"([.!?])\s*\n", r"\1\n", teksto)      # fine frase: va a capo
    teksto = re.sub(r",\s*\n", ", ", teksto)
    teksto = re.sub(r";\s*\n", "; ", teksto)
    teksto = re.sub(r":\s*\n", ":\n", teksto)
    teksto = re.sub(r"(?<![.,;:!?])\n", " ", teksto)       # riga spezzata → spazio
    paragrafoj = [p.strip() for p in teksto.split("\n\n") if p.strip()]
    return "\n\n".join(paragrafoj)


def run(ctx):
    ctx.apply(rekonstrui_paragrafojn)
