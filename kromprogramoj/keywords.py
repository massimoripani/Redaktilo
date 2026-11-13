# -*- coding: utf-8 -*-
"""Eltiras vortojn kun majuskla komenco (el sxlosilaj_OK.py / art_keywords_OK.py).

Se la teksto jam enhavas <sv>...</sv>, ĝi ĝisdatigas ĝin; alie enmetas la blokon ĉe la kursoro.
"""
import re
import monato_common as mc

CATEGORY = "Konvertiloj"
NAME = "Teksto → Ŝlosilvortoj"


def run(ctx):
    parole = sorted(set(p.strip() for p in mc.estrai_parole(ctx.text)))
    if not parole:
        ctx.info("Neniu vorto kun majuskla komenco trovita.")
        return
    elenco = ", ".join(parole)
    text = ctx.text
    m = re.search(r"<sv>(.*?)</sv>", mc.blank_comments(text), re.DOTALL)
    if m:
        if ctx.confirm(f"Trovitaj {len(parole)} vortoj.\nĈu anstataŭigi la enhavon de <sv>?\n\n{elenco[:400]}"):
            ctx.set_text(text[:m.start(1)] + elenco + text[m.end(1):])
    else:
        if ctx.confirm(f"Trovitaj {len(parole)} vortoj.\nĈu enmeti <sv> ĉe la kursoro?\n\n{elenco[:400]}"):
            ctx.insert(f"<sv>{elenco}</sv>")
