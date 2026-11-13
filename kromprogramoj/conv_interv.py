# -*- coding: utf-8 -*-
"""Teksto de intervjuo → Monato-XML (el intervjuo_ok.py).

Ĉiu alineo konservas la originalan tekston en komento 'originala teksto'
kaj ricevas komenton 'faktokontrolo'. Ne kreas ŝlosilvortojn.
"""

CATEGORY = "Konvertiloj"
NAME = "Teksto → intervjuo"

RUBRICA = ""
PRIORITA = "prio x"
KOD = ""
AUTORE = ""
COGNOME = ""
NOTA_FINALE = ""


def build(testo):
    out = f"""<!DOCTYPE art SYSTEM "monato.dtd">

<!--

verkita kaj redaktita de {AUTORE} {COGNOME} redaktita sed NEreviziita versio

revizita de

-->

<art>

<rub>{RUBRICA}</rub>

<inf>{PRIORITA}
</inf>
<sv>

</sv>

<n-ro>
??????
</n-ro>
"""
    for par in testo.splitlines():
        par = par.strip()
        if not par:
            continue
        out += f"\n\n<p>\n    {par}\n</p>\n\n"
        out += f"<!-- originala teksto\n\n{par}\n-->\n<!-- faktokontrolo\n-->\n\n"
    out += f"""<kod>{KOD}</kod>
<aut>{AUTORE} <mm>{COGNOME}</mm></aut>
<!-- {NOTA_FINALE}
-->


</art>
"""
    return out


def run(ctx):
    testo = ctx.text
    if "<art>" in testo and not ctx.confirm(
            "La teksto jam enhavas <art>: ĝi ŝajnas jam esti Monato-artikolo.\nĈu konverti tamen?"):
        return
    ctx.set_text(build(testo))
    ctx.status("Konvertita al Monato-intervjuo (Ctrl+Z por malfari)")
