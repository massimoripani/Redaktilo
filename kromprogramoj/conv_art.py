# -*- coding: utf-8 -*-
"""Simpla teksto → artikolo kun la konvencioj de Monato (el trasformaOK.py).

Por ŝanĝi rubrikon, prioritaton aŭ kapkomenton, redaktu la konstantojn sube.
"""
import monato_common as mc

CATEGORY = "Konvertiloj"
NAME = "Teksto → XML-dokumento"

RUBRICA = "Politiko"
PRIORITA = "prio 3"

INTESTAZIONE = """<!DOCTYPE art SYSTEM "monato.dtd">
<!--
-->
"""


def build(testo):
    parole = sorted(set(p.strip() for p in mc.estrai_parole(testo)))
    out = INTESTAZIONE + "\n<art>\n"
    out += f"<rub>{RUBRICA}</rub>\n"
    out += f"<inf>{PRIORITA}</inf>\n"
    out += f"<sv>{', '.join(parole)}</sv>\n"
    out += "<n-ro>??????</n-ro>\n<tt></tt>\n<t></t>\n"
    for par in testo.splitlines():
        par = par.strip()
        if not par:
            continue            # le righe vuote non generano <p> vuoti
        out += f"\n<p>{par}</p>\n"
    out += "\n<kod></kod>\n<aut>Nomo <mm>FamiliaNomo</mm></aut>\n<!--\n-->\n</art>\n"
    return out


def run(ctx):
    testo = ctx.text
    if "<art>" in testo and not ctx.confirm(
            "La teksto jam enhavas <art>: ĝi ŝajnas jam esti Monato-artikolo.\nĈu konverti tamen?"):
        return
    ctx.set_text(build(testo))        # malfarebla per Ctrl+Z
    ctx.status("Konvertita al Monato-artikolo (Ctrl+Z por malfari)")
