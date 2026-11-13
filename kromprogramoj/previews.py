# -*- coding: utf-8 -*-
"""HTML-antaŭvido en la retumilo, per htmlumilo.py (definitiva versio)."""
import contextlib
import io
import os
import tempfile
import webbrowser

import htmlumilo

CATEGORY = "Kontroliloj"
NAME = "Antaŭrigardo en la retumilo"


def _eo(msg):
    """Tradukas la italajn mesaĝojn de htmlumilo.py (kiu restas netuŝita)."""
    for a, b in (("File HTML creato", "HTML-dosiero kreita"),
                 ("Tag senza corrispondenza HTML", "Etikedo sen respondo en HTML"),
                 ("Errore nel parsing XML", "Eraro dum analizo de XML")):
        msg = msg.replace(a, b)
    return msg


def run(ctx):
    tmpdir = tempfile.mkdtemp(prefix="monato_")
    src = os.path.join(tmpdir, "articolo.xml")
    dst = os.path.join(tmpdir, "articolo.html")
    with open(src, "w", encoding="utf-8") as f:
        f.write(ctx.text)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        htmlumilo.convert_xml_to_html(src, dst)
    messaggi = [_eo(l.strip()) for l in buf.getvalue().splitlines() if l.strip()]

    if not os.path.exists(dst):
        ctx.report("Antaŭvido malsukcesis", [m for m in messaggi if "kreita" not in m]
                   or ["Nekonata eraro"])
        return
    avvisi = [m for m in messaggi if "kreita" not in m]
    if avvisi:
        ctx.report("Antaŭvido malfermita, kun avertoj", avvisi)
    webbrowser.open("file://" + dst)
