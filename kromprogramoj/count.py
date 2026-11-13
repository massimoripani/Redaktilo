# -*- coding: utf-8 -*-
"""Longo de la artikolo en signoj, kalkulita ekde <tt> (kiel htmlumilo)."""
import re
import monato_common as mc

CATEGORY = "Aliaj iloj"
NAME = "Kvanto de tajperoj (ekde <tt>)"


def run(ctx):
    text = mc.blank_comments(ctx.text)
    i = text.find("<tt>")
    if i < 0:
        ctx.warn("Mi ne trovas la etikedon <tt>: la kalkulo komenciĝas de tie.")
        return
    plain = re.sub(r"<[^>]*>", "", text[i:])
    plain = re.sub(r"[ \t]*\n[ \t]*", "\n", plain)
    ctx.info(f"Longo ekde <tt>: {len(plain.strip())} signoj.")
