# -*- coding: utf-8 -*-
"""Literumilo por Esperanto (vortaro Hunspell de LibreOffice + biblioteko "spylls").

 F7  Kontroli ekde la kursoro: por ĉiu nekonata vorto aperas dialogo kun proponoj.
     Butonoj:  Preterpasi (nur ĉi tiu fojo) · Akcepti (ĉiuj ekzemploj en ĉi tiu sesio)
               Anstataŭigi · Anstataŭigi ĉion · Aldoni (al la propra vortaro) · Eliri
 Alia menuero: listo de ĉiuj nekonataj vortoj (rapida, sen proponoj).

 - Ignoras etikedojn, komentojn <!-- -->, <ret>, <kod>, <n-ro>, <inf> k.s.
 - Vortoj en x-sistemo (cxu, sxi) estas akceptataj se ilia kodita formo ekzistas.
 - Propraj vortoj: dosiero vortaroj/propra.txt, aŭ butono "Aldoni".
"""
import os
import queue
import re
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

import monato_common as mc

CATEGORY = "Literumilo"

# Ĉu ignori vortojn kun majuskla komenco meze de frazo kiuj ne troviĝas en la vortaro (nomoj)?
IGNORI_NOMOJN = True
MAKS_PROPONOJ = 10

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIC_DIR = os.path.join(_BASE, "vortaroj")
_DIC_PATH = os.path.join(_DIC_DIR, "eo", "eo")
_OWN_PATH = os.path.join(_DIC_DIR, "propra.txt")

_dictionary = None
_sugg_cache = {}

FINAJXOJ = {"", "o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "en",
            "i", "u", "as", "is", "os", "us", "j", "n"}
_FINAJXOJ_LONGA = sorted((f for f in FINAJXOJ if f), key=len, reverse=True)

_X = {"cx": "ĉ", "gx": "ĝ", "hx": "ĥ", "jx": "ĵ", "sx": "ŝ", "ux": "ŭ"}
_X_RE = re.compile("(?i)(c|g|h|j|s|u)x")

_WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")
_SKIP_BLOCKS = re.compile(r"<(ret|kod|n-ro|inf|lig|loko|retfoto)>.*?</\1>", re.DOTALL)
_FRAZKOMENCO = ("", ".", "!", "?", ":", "„", "“", '"', "»", "«")


# ------------------------------------------------------------------ vortaro
def _load():
    global _dictionary
    if _dictionary is None:
        from spylls.hunspell import Dictionary      # pip install spylls
        _dictionary = Dictionary.from_files(_DIC_PATH)
    return _dictionary


def _own_roots():
    roots = set()
    try:
        with open(_OWN_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    roots.add(line.lower())
    except OSError:
        pass
    return roots


def _own_ok(word, roots):
    w = word.lower()
    return any(w.startswith(r) and w[len(r):] in FINAJXOJ for r in roots)


def _radiko(word):
    """Forigas gramatikan finaĵon (holivudaj → holivud), se restas almenaŭ 3 literoj."""
    w = word.strip().lower()
    for f in _FINAJXOJ_LONGA:
        if w.endswith(f) and len(w) - len(f) >= 3:
            return w[:-len(f)]
    return w


def _add_own(word):
    """Aldonas la radikon al vortaroj/propra.txt. Revenas la aldonitan radikon."""
    root = _radiko(word)
    os.makedirs(_DIC_DIR, exist_ok=True)
    if root not in _own_roots():
        with open(_OWN_PATH, "a", encoding="utf-8") as f:
            f.write(root + "\n")
    return root


def _unx(word):
    def rep(m):
        base = m.group(0)
        out = _X[base.lower()]
        return out.upper() if base[0].isupper() else out
    return _X_RE.sub(rep, word)


# --------------------------------------------------------------- analizo
def _mask(text):
    """Teksto kun malplenigitaj komentoj/etikedoj (samaj pozicioj kaj linioj)."""
    t = mc.blank_comments(text)
    t = _SKIP_BLOCKS.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), t)
    t = re.sub(r"<[^>]*>", lambda m: " " * len(m.group(0)), t)
    t = re.sub(r"&[A-Za-z0-9#]+;", lambda m: " " * len(m.group(0)), t)
    return t


def _prev_char(text, pos):
    i = pos - 1
    while i >= 0 and text[i] in " \t\r\n":
        i -= 1
    return text[i] if i >= 0 else ""


def _ok(d, word, roots):
    for w in {word, _unx(word)}:
        if d.lookup(w) or d.lookup(w.lower()) or d.lookup(w.capitalize()):
            return True
    return _own_ok(word, roots) or _own_ok(_unx(word), roots)


def _sospetta(t, m, d, roots):
    """Ĉu la trovita vorto estas nekonata (kaj ne ignorinda)?"""
    w = m.group(0)
    if len(w) < 2 or _ok(d, w, roots):
        return False
    if w.isupper() and len(w) <= 5:                      # mallongigoj: FEL, UEA...
        return False
    mezo = _prev_char(t, m.start()) not in _FRAZKOMENCO
    if IGNORI_NOMOJN and w[0].isupper() and not w.isupper() and mezo:
        return False
    return True


def trovu_erarojn(text, d=None, roots=None):
    """Listo de (vorto, unua linio, kiom_foje), sen proponoj (rapida)."""
    d = d or _load()
    roots = _own_roots() if roots is None else roots
    t = _mask(text)
    trovitaj = {}
    for m in _WORD.finditer(t):
        if not _sospetta(t, m, d, roots):
            continue
        w = m.group(0)
        if w in trovitaj:
            trovitaj[w][1] += 1
        else:
            trovitaj[w] = [t.count("\n", 0, m.start()) + 1, 1]
    return [(w, v[0], v[1]) for w, v in sorted(trovitaj.items(), key=lambda kv: kv[1][0])]


def _sekva_nekonata(text, d, roots, pos, limit, ignori):
    """Unua nekonata vorto kiu finiĝas post 'pos' kaj komenciĝas antaŭ 'limit'."""
    t = _mask(text)
    for m in _WORD.finditer(t):
        if m.end() <= pos:
            continue
        if limit is not None and m.start() >= limit:
            return None
        w = m.group(0)
        if w.lower() in ignori:
            continue
        if _sospetta(t, m, d, roots):
            return w, m.start(), m.end()
    return None


# --------------------------------------------------------------- dialogo
class Dialogo:
    """Dialogo "Nekonata vorto" kun proponoj (kalkulataj en aparta fadeno)."""

    def __init__(self, ctx, dic, word, start):
        self.ctx, self.dic, self.word, self.start = ctx, dic, word, start
        self.result = ("eliri", "")
        r = ctx.root
        w = self.win = tk.Toplevel(r)
        w.title("Literumilo")
        w.transient(r)
        w.resizable(False, False)

        font = ctx.text_widget.cget("font")
        self._bold = tkfont.Font(font=font)
        self._bold.configure(weight="bold")

        left = ttk.Frame(w, padding=(12, 10, 6, 12))
        left.grid(row=0, column=0)
        right = ttk.Frame(w, padding=(6, 10, 12, 12))
        right.grid(row=0, column=1, sticky="n")

        ttk.Label(left, text="Nekonata vorto:").pack(anchor="w")
        tk.Label(left, text=word, font=self._bold, bg="#f0f0f0", anchor="w",
                 relief="sunken", padx=6, pady=3).pack(fill="x", pady=(2, 8))

        self.prop_var = tk.StringVar(value="Serĉado de proponoj…")
        ttk.Label(left, textvariable=self.prop_var).pack(anchor="w")
        lf = ttk.Frame(left)
        lf.pack(fill="x", pady=(2, 8))
        self.lb = tk.Listbox(lf, height=6, width=32, font=font, exportselection=False)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")

        self.var = tk.StringVar(value=word)
        self.entry = ttk.Entry(left, textvariable=self.var, font=font, width=34)
        self.entry.pack(fill="x")

        self.buttons = []
        for label, act in (("Preterpasi", "preterpasi"), ("Akcepti", "akcepti"),
                           ("Anstataŭigi", "anstatauxi"), ("Anstataŭigi ĉion", "anstatauxi_cxion"),
                           ("Aldoni", "aldoni"), ("Eliri", "eliri")):
            b = ttk.Button(right, text=label, width=17, command=lambda a=act: self._end(a))
            b.pack(pady=2)
            self.buttons.append(b)

        self.lb.bind("<<ListboxSelect>>", self._on_select)
        self.lb.bind("<Double-Button-1>", lambda e: self._on_select() or self._end("anstatauxi"))
        self.entry.bind("<Return>", lambda e: self._end("anstatauxi"))
        w.bind("<Escape>", lambda e: self._end("eliri"))
        w.protocol("WM_DELETE_WINDOW", lambda: self._end("eliri"))

        self._place()
        self._start_suggest()

    # -- posizione: lontano dalla parola evidenziata
    def _place(self):
        w, r, tw = self.win, self.ctx.root, self.ctx.text_widget
        w.update_idletasks()
        W, H = w.winfo_width(), w.winfo_height()
        rx, ry, rw, rh = r.winfo_rootx(), r.winfo_rooty(), r.winfo_width(), r.winfo_height()
        bb = tw.bbox(self.ctx.offset_to_index(self.start))
        word_y = tw.winfo_rooty() + (bb[1] if bb else 0)
        y = ry + rh - H - 50 if word_y < ry + rh / 2 else ry + 60
        x = rx + (rw - W) // 2
        x = max(0, min(x, w.winfo_screenwidth() - W))
        y = max(0, min(y, w.winfo_screenheight() - H - 40))
        w.geometry(f"+{x}+{y}")

    # -- proposte in un thread (la finestra resta reattiva)
    def _start_suggest(self):
        if self.word in _sugg_cache:
            self._fill(_sugg_cache[self.word])
            return
        q = queue.Queue()

        def work():
            try:
                res = list(self.dic.suggest(_unx(self.word)))[:MAKS_PROPONOJ]
            except Exception:
                res = []
            q.put(res)

        threading.Thread(target=work, daemon=True).start()
        self._poll(q)

    def _poll(self, q):
        try:
            if not self.win.winfo_exists():
                return
            try:
                res = q.get_nowait()
            except queue.Empty:
                self.win.after(80, self._poll, q)
                return
            _sugg_cache[self.word] = res
            self._fill(res)
        except tk.TclError:
            pass

    def _fill(self, sugg):
        self.lb.delete(0, "end")
        for s in sugg:
            self.lb.insert("end", s)
        self.prop_var.set("Proponoj:" if sugg else "Neniu propono.")

    def _on_select(self, _e=None):
        sel = self.lb.curselection()
        if sel:
            self.var.set(self.lb.get(sel[0]))

    def _end(self, action):
        self.result = (action, self.var.get().strip())
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    def show(self):
        w = self.win
        try:
            w.grab_set()
        except tk.TclError:
            pass
        self.buttons[0].focus_set()
        w.wait_window()
        return self.result


# ---------------------------------------------------------------- agoj
def _preparo(ctx):
    try:
        return _load()
    except ImportError:
        ctx.warn("Mankas la pakaĵo «spylls».\nInstalu ĝin per:  pip install spylls")
    except Exception as e:
        ctx.warn(f"Ne eblas ŝargi la vortaron ({_DIC_PATH}.dic):\n{e}")
    return None


def kontroli_interage(ctx):
    """F7: kontrolas ekde la kursoro; ĉe la fino proponas daŭrigi de la komenco."""
    d = _preparo(ctx)
    if d is None:
        return
    tw = ctx.text_widget
    tw.tag_configure("literuma", background="#ffcc00", foreground="black")
    roots = _own_roots()
    ignori = set()                 # "Akcepti": ignoritaj en ĉi tiu sesio
    anstatauxoj = {}               # "Anstataŭigi ĉion"
    nombroj = {"anstatauxitaj": 0, "aldonitaj": 0, "preterpasitaj": 0}
    origin = ctx.cursor_offset()
    pos, limit, pass_no, eliris = origin, None, 1, False

    # se la kursoro estas meze de vorto, komenci ĉe ĝia komenco
    while True:
        trovo = _sekva_nekonata(ctx.text, d, roots, pos, limit, ignori)
        if trovo is None:
            if pass_no == 1 and origin > 0 and \
                    ctx.confirm("Atingis la finon de la teksto.\nĈu daŭrigi de la komenco?"):
                pass_no, pos, limit = 2, 0, origin
                continue
            break
        w, start, end = trovo

        if w in anstatauxoj:                       # jam elektita "Anstataŭigi ĉion"
            nova = anstatauxoj[w]
            ctx.replace_range(start, end, nova)
            nombroj["anstatauxitaj"] += 1
            delta = len(nova) - (end - start)
            pos = start + len(nova)
            if limit is not None:
                limit += delta
            continue

        ctx.select_range(start, end)
        tw.tag_add("literuma", ctx.offset_to_index(start), ctx.offset_to_index(end))
        ctx.root.update_idletasks()
        agon, teksto = Dialogo(ctx, d, w, start).show()
        tw.tag_remove("literuma", "1.0", "end")

        if agon == "eliri":
            eliris = True
            break
        if agon == "preterpasi":
            nombroj["preterpasitaj"] += 1
            pos = end
        elif agon == "akcepti":
            ignori.add(w.lower())
            pos = end
        elif agon == "aldoni":
            roots.add(_add_own(teksto or w))
            nombroj["aldonitaj"] += 1
            pos = end
        elif agon in ("anstatauxi", "anstatauxi_cxion"):
            if not teksto or teksto == w:          # nenio ŝanĝita: kiel "Preterpasi"
                pos = end
                continue
            if agon == "anstatauxi_cxion":
                anstatauxoj[w] = teksto
            ctx.replace_range(start, end, teksto)
            nombroj["anstatauxitaj"] += 1
            delta = len(teksto) - (end - start)
            pos = start + len(teksto)
            if limit is not None:
                limit += delta

    tw.tag_remove("literuma", "1.0", "end")
    tw.focus_set()
    resumo = (f"{nombroj['anstatauxitaj']} anstataŭigoj, "
              f"{nombroj['aldonitaj']} aldonoj al la vortaro, "
              f"{nombroj['preterpasitaj']} preterpasoj")
    if eliris:
        ctx.status("Literumado interrompita: " + resumo)
    else:
        ctx.status("Literumado finita: " + resumo)
        ctx.info("Literumado finita.\n\n" + resumo)


def listo(ctx):
    d = _preparo(ctx)
    if d is None:
        return
    eraroj = trovu_erarojn(ctx.text, d)
    if not eraroj:
        ctx.info("Neniu literuma eraro trovita.")
        return
    items = [(line, f"«{w}»" + (f" ({n}×)" if n > 1 else "")) for w, line, n in eraroj]
    ctx.report(f"Literumado: {len(eraroj)} nekonataj vortoj  (F7 por kontroli kun proponoj)", items)


def aldoni_vorton(ctx):
    w = ctx.selection()
    w = (w or "").strip() or (ctx.ask("Vorto aldonota al la propra vortaro:") or "").strip()
    if not w or not _WORD.fullmatch(w):
        return
    root = _add_own(w)
    ctx.status(f"«{root}» aldonita al vortaroj/propra.txt (akceptas ĉiujn gramatikajn finaĵojn)")


ACTIONS = [
    ("Kontrolo ekde la kursoro", kontroli_interage, "F7"),
    ("Listo de nekonataj vortoj", listo),
    ("Aldonu al la vortaro", aldoni_vorton),
]
HOTKEYS = {"<F7>": kontroli_interage}
