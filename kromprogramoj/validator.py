# -*- coding: utf-8 -*-
"""Kontrolas Monato-etikedojn kaj HTML-komentojn (Python-versio de validatore.php)."""
import monato_common as mc

CATEGORY = "Kontroliloj"
NAME = "Etikedoj kaj komentoj"


def run(ctx):
    text = ctx.text
    errors = mc.validate_tags(text) + mc.validate_comments(text)
    errors.sort(key=lambda e: e[0])
    if not errors:
        ctx.info("Neniu eraro trovita.")
        return
    n = len(errors)
    ctx.report(f"Kontrolo: {n} " + ("problemo" if n == 1 else "problemoj"), errors)
