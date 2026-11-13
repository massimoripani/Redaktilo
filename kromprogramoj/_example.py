# -*- coding: utf-8 -*-
"""EKZEMPLO DE KROMPROGRAMO (la dosiernomo komenciĝas per "_", do ĝi NE estas ŝargata).

Por krei kromprogramon: kopiu ĉi tiun dosieron en ĉi tiun dosierujon, forigu la "_" el la nomo,
kaj elektu Kromprogramoj → Reŝargi kromprogramojn (aŭ restartigu la redaktilon).

Kromprogramo estas .py-dosiero kun:
    CATEGORY = "Kontrolo"        submenuo en la menuo Kromprogramoj
    NAME     = "Teksto de menuo" menuero
    def run(ctx): ...            funkcio ruliĝanta kiam oni elektas la menueron

Aŭ, por pluraj menueroj en unu dosiero:
    ACTIONS = [("Ero 1", funkcio1), ("Ero 2", funkcio2)]   (ĉiu funkcio ricevas ctx)

Kion ofertas `ctx`:
    ctx.text                  la tuta teksto de la dokumento
    ctx.selection()           la elektita teksto (aŭ None)
    ctx.set_text(s)           anstataŭigas la tutan tekston (malfarebla per Ctrl+Z)
    ctx.replace_selection(s)  anstataŭigas la elekton
    ctx.insert(s)             enmetas ĉe la kursoro
    ctx.apply(fn)             aplikas fn(teksto) al la elekto, aŭ al ĉio se nenio estas elektita
    ctx.report(titolo, eroj)  panelo de rezultoj; eroj = [(linio, mesaĝo), ...]
                              (duoble klaku eron → salto al la linio)
    ctx.info(msg) / ctx.warn(msg) / ctx.confirm(msg) / ctx.ask(msg)
    ctx.status(msg)           mesaĝo en la statobreto
    ctx.path                  vojo de la malfermita dosiero (aŭ None)

Por interagaj kromprogramoj (vidu literumado.py):
    ctx.root, ctx.text_widget       la ĉefa fenestro kaj la tekstokampo (tkinter)
    ctx.cursor_offset()             pozicio de la kursoro (nombro de signoj de la komenco)
    ctx.offset_to_index(n)          pozicio n -> indekso de Tk
    ctx.select_range(a, b)          elektas kaj montras la intervalon a..b
    ctx.replace_range(a, b, s)      anstataŭigas la intervalon (ĉiu anstataŭigo = unu Ctrl+Z)

Klavo kaj menua indiko:
    ACTIONS = [("Ero", funkcio, "F7")]       (3-a elemento: klavo montrata en la menuo)
    HOTKEYS = {"<F7>": funkcio}              (la klavo ruligas la funkcion)

Pretaj funkcioj: vidu monato_common.py (kontrolo de etikedoj, ŝlosilvortoj, ktp.).

LIMO en la .exe-versio: kromprogramoj povas uzi la norman bibliotekon de Python
(re, os, json, csv, datetime, difflib, urllib.parse, xml.etree, ktp. — vidu konstrui_exe.bat),
sed ne eksterajn pakaĵojn (requests, numpy...) krom se oni aldonas ilin al la konstruo.
"""

CATEGORY = "Ekzemplo"
NAME = "Majuskloj"


def run(ctx):
    ctx.apply(str.upper)
