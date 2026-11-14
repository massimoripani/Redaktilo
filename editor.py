#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Redaktilo: UTF-8-redaktilo kun kromprogramoj (menuo "Kromprogramoj").

Lanĉo:  python editor.py [dosiero]
La kromprogramoj estas la .py-dosieroj en la dosierujo "kromprogramoj"
(vidu kromprogramoj/_esempio.py). En la .exe-versio tiu dosierujo troviĝas apud la .exe.
"""
import csv
import importlib
import importlib.util
import os
import re
import sys
import traceback
import json
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, ttk

FROZEN = getattr(sys, "frozen", False)          # True quando gira come .exe
BASE = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.join(BASE, "kromprogramoj")   # accanto all'exe: qui si aggiungono i nuovi plugin
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import monato_common as mc  # noqa: E402


APP_NAME = "Redaktilo"
VERSION = "2.32"
CATEGORY_ORDER = ["Konvertiloj", "Kontroliloj", "Literumilo", "Aliaj iloj"]

X_MAP = {"c": "ĉ", "g": "ĝ", "h": "ĥ", "j": "ĵ", "s": "ŝ", "u": "ŭ",
         "C": "Ĉ", "G": "Ĝ", "H": "Ĥ", "J": "Ĵ", "S": "Ŝ", "U": "Ŭ"}

# (voce di menu, tag, scorciatoia mostrata, sequenza Tk o None)
TAG_MENU = [
    ("Dika  <d>", "d", "Ctrl+B", "<Control-b>"),
    ("Kursiva  <k>", "k", "Ctrl+I", "<Control-i>"),
    ("Citiloj  <c>", "c", "Ctrl+Shift+Q", "<Control-Q>"),
    ("Malgrandaj majuskloj  <mm>", "mm", "Ctrl+Shift+M", "<Control-M>"),
    ("Ruĝa  <r>", "r", None, None),
    ("Malaltigo  <sub>", "sub", None, None),
    ("Altigo  <sup>", "sup", None, None),
    ("Retadreso  <ret>", "ret", None, None),
    ("Alineo  <p>", "p", "Ctrl+Shift+P", "<Control-P>"),
    ("Komento  <!-- -->", "!--", "Ctrl+Shift+C", "<Control-C>"),
]


# =====================================================================
# Klavkombinoj (tasti rapidi): conversione, salvataggio
# =====================================================================
def _config_dir():
    """Cartella dei dati utente (scrivibile anche se il programma è in Program Files)."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "Redaktilo")


CONFIG_DIR = _config_dir()
KEYS_FILE = os.path.join(CONFIG_DIR, "klavkombinoj.json")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
LANG_DIR = os.path.join(BASE, "lingvoj")      # pacchetti linguistici: lingvoj/<kodo>.json
DEFAULT_LANG = "eo"

# ---------------------------------------------------------------- lingvoj
# La lingvo-fonto estas Esperanto: la ĉenoj en la kodo servas kiel ŝlosiloj.
# Dosiero lingvoj/<kodo>.json: {"_meta": {"nomo": "Italiano"}, "ĉenoj": {"Esperanta teksto": "traduko"}}
# Aldonaj dosieroj lingvoj/<kodo>.<io>.json estas kunfanditaj (ekz. por kromprogramoj).
_TR = {}
CURRENT_LANG = DEFAULT_LANG


def tr(s):
    """Traduko de ĉeno (se mankas, la originala Esperanta teksto)."""
    return _TR.get(s, s)


def available_languages():
    """[(kodo, nomo)] el la dosierujo lingvoj/."""
    langs = []
    try:
        names = sorted(os.listdir(LANG_DIR))
    except OSError:
        return [(DEFAULT_LANG, "Esperanto")]
    for fn in names:
        if fn.endswith(".json") and fn.count(".") == 1:
            code = fn[:-5]
            try:
                with open(os.path.join(LANG_DIR, fn), encoding="utf-8") as f:
                    nomo = json.load(f).get("_meta", {}).get("nomo", code)
            except (OSError, ValueError, AttributeError):
                continue
            langs.append((code, nomo))
    return langs or [(DEFAULT_LANG, "Esperanto")]


def load_language(code):
    """Ŝargas lingvan pakaĵon; ne ekzistanta/rompita -> Esperanto."""
    global _TR, CURRENT_LANG
    table = {}
    try:
        names = sorted(os.listdir(LANG_DIR))
    except OSError:
        names = []
    for fn in names:
        if fn.endswith(".json") and (fn == code + ".json" or fn.startswith(code + ".")):
            try:
                with open(os.path.join(LANG_DIR, fn), encoding="utf-8") as f:
                    table.update(json.load(f).get("ĉenoj", {}))
            except (OSError, ValueError, AttributeError):
                pass
    _TR = {k: v for k, v in table.items() if v}
    CURRENT_LANG = code if table else DEFAULT_LANG


def load_settings():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


load_language(os.environ.get("REDAKTILO_LINGVO") or load_settings().get("lingvo", DEFAULT_LANG))

_MOD_NAMES = {"Control": "Ctrl", "Alt": "Alt", "Shift": "Shift", "Mod1": "Alt",
              "Command": "Cmd", "Meta": "Alt"}
_KEY_NAMES = {"Prior": "PgUp", "Next": "PgDn", "Return": "Enter", "Escape": "Esc",
              "BackSpace": "Retropaŝo", "Delete": "Del", "Insert": "Ins",
              "space": "Spaco", "Tab": "Tab", "minus": "-", "plus": "+",
              "equal": "=", "comma": ",", "period": ".", "slash": "/"}
_PURE_MODS = {"Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R",
              "Meta_L", "Meta_R", "Super_L", "Super_R", "Caps_Lock", "Num_Lock",
              "ISO_Level3_Shift", "Mode_switch"}
_SHIFTABLE = {"Tab", "Return", "space", "Prior", "Next", "Home", "End", "Insert",
              "Delete", "BackSpace", "Left", "Right", "Up", "Down"}


def seq_to_display(seq):
    """'<Control-S>' -> 'Ctrl+Shift+S'"""
    if not seq:
        return ""
    parts = seq.strip("<>").split("-")
    key = parts[-1] if parts[-1] else "-"
    mods = [_MOD_NAMES.get(m, m) for m in parts[:-1]]
    if len(key) == 1 and key.isalpha() and key.isupper() and "Shift" not in mods:
        mods.append("Shift")
    order = {"Ctrl": 0, "Alt": 1, "Cmd": 1, "Shift": 2}
    mods.sort(key=lambda m: order.get(m, 3))
    key = _KEY_NAMES.get(key, key.upper() if len(key) == 1 else key)
    return "+".join(mods + [key])


def event_to_seq(event):
    """Evento di tastiera -> sequenza Tk (None se è solo un modificatore o non valida)."""
    ks = event.keysym
    if ks in _PURE_MODS:
        return None
    st = event.state
    ctrl = bool(st & 0x4)
    shift = bool(st & 0x1)
    alt = bool(st & 0x20000) if sys.platform.startswith("win") else bool(st & 0x8)
    is_f = bool(re.fullmatch(r"F\d{1,2}", ks))
    if len(ks) == 1 and ks.isalpha():
        key = ks.upper() if shift else ks.lower()
        shift_mod = False
    elif len(ks) == 1 or ks in ("minus", "plus", "equal", "comma", "period", "slash"):
        key, shift_mod = ks, False
    elif is_f or ks in _SHIFTABLE:
        key, shift_mod = ks, shift
    else:
        return None
    if not (ctrl or alt) and not is_f:
        return None            # un tasto semplice sarebbe usato per scrivere
    mods = (["Control"] if ctrl else []) + (["Alt"] if alt else []) + (["Shift"] if shift_mod else [])
    return "<" + "-".join(mods + [key]) + ">"


def load_user_keys():
    try:
        with open(KEYS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        keys = data.get("klavoj", {})
        return {str(k): str(v) for k, v in keys.items()}
    except (OSError, ValueError, AttributeError):
        return {}


def save_user_keys(keys):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump({"versio": 1, "klavoj": keys}, f, ensure_ascii=False, indent=2)


# =====================================================================
# Dialoghi in esperanto (quelli di sistema usano la lingua di Windows)
# =====================================================================
def ask_dialog(parent, title, text, buttons, entry=None, default=0):
    """Dialogo modale. Ritorna (indice del bottone o None, testo dell'eventuale campo)."""
    d = tk.Toplevel(parent)
    d.title(tr(title))
    d.transient(parent)
    d.resizable(False, False)
    buttons = [tr(b) for b in buttons]
    res = {"btn": None, "text": None}
    var = tk.StringVar(value=entry or "")
    ttk.Label(d, text=tr(text), justify="left", wraplength=480, padding=(16, 14)).pack()
    e = None
    if entry is not None:
        e = ttk.Entry(d, textvariable=var, width=50)
        e.pack(padx=16, pady=(0, 8))
    bar = ttk.Frame(d)
    bar.pack(pady=(0, 12))

    def press(i):
        res["btn"], res["text"] = i, var.get()
        d.destroy()

    default_btn = None
    for i, b in enumerate(buttons):
        btn = ttk.Button(bar, text=b, command=lambda i=i: press(i))
        btn.pack(side="left", padx=5)
        if i == default:
            default_btn = btn
    d.bind("<Return>", lambda ev: press(default))
    d.bind("<Escape>", lambda ev: d.destroy())
    d.update_idletasks()
    try:
        x = parent.winfo_rootx() + (parent.winfo_width() - d.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - d.winfo_height()) // 3
        d.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        d.grab_set()
    except tk.TclError:
        pass
    (e or default_btn).focus_set()
    parent.wait_window(d)
    return res["btn"], res["text"]


def show_info(parent, msg, title=None):
    ask_dialog(parent, title or "Informo", msg, ["Bone"])


def show_warn(parent, msg):
    ask_dialog(parent, "Averto", msg, ["Bone"])


def show_error(parent, msg):
    ask_dialog(parent, "Eraro", msg, ["Bone"])


def yes_no(parent, msg):
    return ask_dialog(parent, APP_NAME, msg, ["Jes", "Ne"])[0] == 0


def yes_no_cancel(parent, msg):
    b = ask_dialog(parent, APP_NAME, msg, ["Jes", "Ne", "Rezigni"], default=0)[0]
    return {0: True, 1: False}.get(b)           # None = rezigni


def ask_text(parent, msg, initial=""):
    b, t = ask_dialog(parent, APP_NAME, msg, ["Bone", "Rezigni"], entry=initial)
    return t if b == 0 else None


# =====================================================================
# Cerca/sostituisci: caratteri speciali ed espressioni regolari
# =====================================================================
# \\  \n  \t  \r  \r\n  \uXXXX  \xHH   (tutto il resto resta com'è)
_ESC_TOKEN = re.compile(r"\\(\\|r\\n|n|t|r|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2})")
# nei modelli regex/sostituzioni: si trattano solo \\, \r\n e (nella sostituzione) \u / \x
_ESC_PATTERN = re.compile(r"\\(\\|r\\n)")
_ESC_TEMPLATE = re.compile(r"\\(\\|r\\n|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2})")


def unescape_literal(s):
    """Modalità testo: \\n \\t \\r \\uXXXX \\xHH \\\\ diventano i caratteri veri.
    \\r\\n vale come un a capo (internamente il testo usa solo \\n)."""
    def rep(m):
        t = m.group(1)
        if t == "\\":
            return "\\"
        if t in ("n", "r\\n"):
            return "\n"
        if t == "t":
            return "\t"
        if t == "r":
            return "\r"
        return chr(int(t[1:], 16))
    return _ESC_TOKEN.sub(rep, s)


def prep_regex_pattern(s):
    """Modello regex: Python capisce già \\n \\t \\uXXXX; qui si riduce solo \\r\\n a \\n."""
    return _ESC_PATTERN.sub(lambda m: m.group(0) if m.group(1) == "\\" else "\\n", s)


def prep_regex_template(s):
    """Sostituzione regex: \\1 \\g<nome> \\n \\t li gestisce re; qui si aggiungono \\uXXXX, \\xHH e \\r\\n."""
    def rep(m):
        t = m.group(1)
        if t == "\\":
            return "\\\\"
        if t == "r\\n":
            return "\\n"
        ch = chr(int(t[1:], 16))
        return "\\\\" if ch == "\\" else ch
    return _ESC_TEMPLATE.sub(rep, s)


def build_search(find, repl, use_regex, use_escapes, match_case):
    """Ritorna (regex compilata, funzione espandi(match) -> testo sostitutivo).
    Può sollevare re.error se il modello non è valido."""
    flags = 0 if match_case else re.IGNORECASE
    if use_regex:
        rx = re.compile(prep_regex_pattern(find), flags | re.MULTILINE)
        tmpl = prep_regex_template(repl)
        return rx, (lambda m: m.expand(tmpl))
    lit = unescape_literal(find) if use_escapes else find
    rep = unescape_literal(repl) if use_escapes else repl
    return re.compile(re.escape(lit), flags), (lambda m: rep)


SEARCH_HELP = """SPECIALAJ SIGNOJ  (en «Serĉi» kaj «Anstataŭigi per»)
  \\n  novlinio              \\t  tabo
  \\r\\n  valoras kiel novlinio (la redaktilo uzas internan \\n)
  \\uXXXX  signo laŭ Unicode (ekz. \\u02BF = ʿ)     \\xHH  signo (2 deksesumaj ciferoj)
  \\\\  la oblikva streko mem

REGULAJ ESPRIMOJ  (se la skatolo estas markita)
  .  ajna signo (ne novlinio)    ^  linikomenco    $  linifino    \\b  vortlimo
  \\d  cifero    \\w  litero/cifero    \\s  spaco    [abc]  unu el    [^abc]  neniu el
  *  0 aŭ pli    +  1 aŭ pli    ?  0 aŭ 1    {2,4}  2 ĝis 4    a|b  a aŭ b
  (…)  grupo; en «Anstataŭigi per»:  \\1  \\2  aŭ  \\g<nomo>
  [\\s\\S]  ĉiu signo, ankaŭ novlinio       (?s)  ĉe la komenco: la punkto trovas ankaŭ novliniojn

EKZEMPLOJ
  Forigi finajn spacojn:      serĉi  [ \\t]+$      anstataŭigi per  (nenio)
  Unu alineo → unu linio:     serĉi  \\n\\n        anstataŭigi per  \\n
  Meti <p> ĉirkaŭ ĉiu linio:  serĉi  ^(.+)$     anstataŭigi per  <p>\\1</p>
 """

# =====================================================================
# Contesto passato ai plugin
# =====================================================================
class Context:
    def __init__(self, app):
        self._app = app

    @property
    def text(self):
        return self._app.get_text()

    @property
    def path(self):
        return self._app.path

    def selection(self):
        return self._app.get_selection()

    def set_text(self, s):
        self._app.set_text(s)

    def replace_selection(self, s):
        self._app.replace_selection(s)

    def insert(self, s):
        self._app.text.insert("insert", s)

    def apply(self, fn):
        sel = self.selection()
        if sel:
            self.replace_selection(fn(sel))
        else:
            self.set_text(fn(self.text))

    def report(self, title, items):
        self._app.show_report(tr(title), items)

    def tr(self, text):
        """Tradukas ĉenon laŭ la elektita lingvo (por kromprogramoj)."""
        return tr(text)

    def info(self, msg):
        show_info(self._app.root, tr(msg))

    def warn(self, msg):
        show_warn(self._app.root, tr(msg))

    def error(self, msg):
        show_error(self._app.root, tr(msg))

    def confirm(self, msg):
        return yes_no(self._app.root, tr(msg))

    def ask(self, msg, initial=""):
        return ask_text(self._app.root, tr(msg), initial)

    def status(self, msg):
        self._app.set_status_message(tr(msg))

    # --- per plugin interattivi (es. literumilo) ---
    @property
    def root(self):
        return self._app.root

    @property
    def text_widget(self):
        return self._app.text

    def offset_to_index(self, offset):
        """Posizione numerica nel testo (0, 1, 2...) -> indice Tk 'riga.colonna'."""
        return self._app.text.index(f"1.0+{offset}c")

    def cursor_offset(self):
        """Posizione del cursore come numero di caratteri dall'inizio."""
        return len(self._app.text.get("1.0", "insert"))

    def select_range(self, start_offset, end_offset):
        """Seleziona e mostra l'intervallo (usa posizioni numeriche)."""
        t = self._app.text
        a, b = self.offset_to_index(start_offset), self.offset_to_index(end_offset)
        t.tag_remove("sel", "1.0", "end")
        t.tag_add("sel", a, b)
        t.mark_set("insert", b)
        t.see(a)

    def replace_range(self, start_offset, end_offset, new):
        """Sostituisce l'intervallo; ogni sostituzione si annulla con un Ctrl+Z."""
        self._app.replace_range(self.offset_to_index(start_offset),
                                self.offset_to_index(end_offset), new)


# =====================================================================
# Documento (una scheda): testo, cronologia undo/redo e risultati propri
# =====================================================================
class Document:
    _counter = 0

    def __init__(self, app, parent):
        Document._counter += 1
        self.number = Document._counter
        self.frame = ttk.Frame(parent)
        self.gutter = tk.Canvas(self.frame, width=48, highlightthickness=0, bg="#f0f0f0")
        self.gutter.pack(side="left", fill="y")
        self.vsb = ttk.Scrollbar(self.frame, orient="vertical")
        self.vsb.pack(side="right", fill="y")
        # ogni Text ha la propria cronologia undo/redo
        self.text = tk.Text(self.frame, undo=True, autoseparators=True, maxundo=-1,
                            wrap="word" if app.wrap.get() else "none", font=app.font,
                            padx=6, pady=4, borderwidth=0, highlightthickness=0, spacing1=1,
                            insertwidth=2, selectbackground="#b4d5fe",
                            selectforeground="black", inactiveselectbackground="#d0d0d0")
        self.text.pack(side="left", fill="both", expand=True)
        self.vsb.configure(command=self.text.yview)
        self.text.tag_configure("tag", foreground="#1f5fbf")
        self.text.tag_configure("unknown", foreground="#c00000", underline=True)
        self.text.tag_configure("comment", foreground="#2e7d32", font=app._italic())
        self.text.tag_configure("hit", background="#fff2a8")
        self.text.tag_raise("sel")
        self.path = None
        self.eol = "\n"
        self.encoding_note = "UTF-8"
        self.dirty = False
        self._last_conv = None
        self._hl_job = None
        # risultati dei plugin di questo documento (None = nessuno)
        self._report_entries = None
        self._report_lines = []
        self._report_items = []
        self._report_title = ""

    def display_name(self):
        if self.path:
            return os.path.basename(self.path)
        n = tr("sennoma")
        return n if self.number == 1 else f"{n} {self.number}"


def _proxy(attr):
    """Attributo dell'App che legge/scrive sul documento corrente."""
    return property(lambda self: getattr(self.doc, attr),
                    lambda self, v: setattr(self.doc, attr, v))


# =====================================================================
# Applicazione
# =====================================================================
class App:
    # il documento corrente: tutto ciò che prima era "del programma" ora è del documento
    text = property(lambda self: self.doc.text)
    gutter = property(lambda self: self.doc.gutter)
    vsb = property(lambda self: self.doc.vsb)
    path = _proxy("path")
    eol = _proxy("eol")
    encoding_note = _proxy("encoding_note")
    dirty = _proxy("dirty")
    _last_conv = _proxy("_last_conv")
    _hl_job = _proxy("_hl_job")
    _report_lines = _proxy("_report_lines")
    _report_items = _proxy("_report_items")
    _report_title = _proxy("_report_title")

    @property
    def doc(self):
        sel = self.nb.select()
        return self._doc_by_tab.get(str(sel)) if sel else None

    def __init__(self, root, path=None):
        self.root = root
        self.docs = []
        self._doc_by_tab = {}
        self.auto_cx = tk.BooleanVar(value=True)
        self.wrap = tk.BooleanVar(value=True)
        self.highlight_on = tk.BooleanVar(value=True)
        self.search_all = tk.BooleanVar(value=False)
        self._status_msg = ""
        recent = load_settings().get("lastatempaj_dosieroj", [])
        self.recent_files = [os.path.abspath(p) for p in recent if isinstance(p, str)][:10] if isinstance(recent, list) else []
        self.plugins = []
        self.plugin_errors = []
        self.commands = {}               # id -> dict(group,label,run,default)
        self._menu_entries = {}          # id -> [(menu, indice)]
        self._bound = []                 # (widget, sequenza) attualmente associati
        self.user_keys = load_user_keys()
        self.ctx = Context(self)

        self._build_ui()
        self._register_builtin_commands()
        self._build_menus()
        self.load_plugins()
        self._build_plugin_menu()
        self._add_document()

        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._update_title()
        self._update_status()
        for pth in ([path] if isinstance(path, str) else (path or [])):
            self.open_file(pth)

    # ------------------------------------------------------------ interfaccia
    def _build_ui(self):
        r = self.root
        r.geometry("1000x700")

        self.status = ttk.Label(r, anchor="w", padding=(8, 3), relief="sunken")
        self.status.pack(side="bottom", fill="x")

        self.main = ttk.Frame(r)
        self.main.pack(side="top", fill="both", expand=True)

        self.font = tkfont.Font(family="DejaVu Sans Mono", size=12)
        for fam in ("Consolas", "DejaVu Sans Mono", "Courier New"):
            if fam in tkfont.families():
                self.font.configure(family=fam)
                break

        self.nb = ttk.Notebook(self.main)
        self.nb.pack(fill="both", expand=True)
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._on_tab_changed())
        self.nb.bind("<Button-3>", self._tab_popup)
        if sys.platform == "darwin":
            self.nb.bind("<Button-2>", self._tab_popup)
        else:
            self.nb.bind("<Button-2>", self._tab_middle_click)
        self._tab_menu = tk.Menu(self.nb, tearoff=0)

        # pannello risultati (appare quando un plugin chiama ctx.report)
        self.panel = ttk.Frame(r)
        head = ttk.Frame(self.panel)
        head.pack(fill="x")
        self.panel_title = ttk.Label(head, text="", font=("TkDefaultFont", 10, "bold"))
        self.panel_title.pack(side="left", padx=6, pady=2)
        ttk.Button(head, text="✕", width=3, command=self.hide_report).pack(side="right", padx=4)
        ttk.Button(head, text=tr("Konservi…"), command=self.report_save).pack(side="right", padx=2)
        ttk.Button(head, text=tr("Kopii ĉion"), command=self.report_copy_all).pack(side="right", padx=2)
        body = ttk.Frame(self.panel)
        body.pack(fill="both", expand=True)
        self.report_list = tk.Listbox(body, height=7, activestyle="dotbox", font=self.font,
                                      selectmode="extended", exportselection=False)
        sb = ttk.Scrollbar(body, orient="vertical", command=self.report_list.yview)
        self.report_list.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.report_list.pack(side="left", fill="both", expand=True)
        self.report_list.bind("<Double-Button-1>", self._report_jump)
        self.report_list.bind("<Return>", self._report_jump)
        self.report_list.bind("<Control-c>", lambda e: (self.report_copy_selected(), "break")[1])
        self.report_list.bind("<Control-a>", lambda e: (self.report_select_all(), "break")[1])
        self._report_menu = tk.Menu(self.report_list, tearoff=0)
        self._report_menu.add_command(label=tr("Kopii elektitajn"), command=self.report_copy_selected)
        self._report_menu.add_command(label=tr("Kopii ĉion"), command=self.report_copy_all)
        self._report_menu.add_command(label=tr("Elekti ĉion"), command=self.report_select_all)
        self._report_menu.add_separator()
        self._report_menu.add_command(label=tr("Konservi…"), command=self.report_save)
        for seq in ("<Button-3>", "<Button-2>"):          # tasto destro (Windows/Linux) e Mac
            self.report_list.bind(seq, self._report_popup)

    def _italic(self):
        f = self.font.copy()
        f.configure(slant="italic")
        return f

    def _build_menus(self):
        r = self.root
        self.menubar = tk.Menu(r)
        r.config(menu=self.menubar)

        m = tk.Menu(self.menubar, tearoff=0)
        self._add_cmd(m, "dosiero.nova")
        self._add_cmd(m, "dosiero.malfermi")
        self.recent_menu = tk.Menu(m, tearoff=0, postcommand=self._populate_recent_menu)
        m.add_cascade(label=tr("Lastatempe malfermitaj"), menu=self.recent_menu)
        self._add_cmd(m, "dosiero.konservi")
        self._add_cmd(m, "dosiero.konservi_kiel")
        m.add_separator()
        self._add_cmd(m, "dosiero.fermi")
        self._add_cmd(m, "dosiero.sekva")
        self._add_cmd(m, "dosiero.antaua")
        m.add_separator()
        self._add_cmd(m, "dosiero.eliri")
        self.menubar.add_cascade(label=tr("Dosiero"), menu=m)

        m = tk.Menu(self.menubar, tearoff=0)
        m.add_command(label=tr("Malfari"), accelerator="Ctrl+Z", command=lambda: self._undo(False))
        self._add_cmd(m, "redakti.refari")
        m.add_separator()
        m.add_command(label=tr("Tondi"), accelerator="Ctrl+X", command=lambda: self.text.event_generate("<<Cut>>"))
        m.add_command(label=tr("Kopii"), accelerator="Ctrl+C", command=lambda: self.text.event_generate("<<Copy>>"))
        m.add_command(label=tr("Alglui"), accelerator="Ctrl+V", command=lambda: self.text.event_generate("<<Paste>>"))
        self._add_cmd(m, "redakti.elekti")
        m.add_separator()
        self._add_cmd(m, "redakti.serci")
        self._add_cmd(m, "redakti.sekva")
        self._add_cmd(m, "redakti.antaua")
        self._add_cmd(m, "redakti.iri")
        self.menubar.add_cascade(label=tr("Redakti"), menu=m)

        m = tk.Menu(self.menubar, tearoff=0)
        for _label, tag, _acc, _seq in TAG_MENU:
            self._add_cmd(m, "etikedo." + tag)
        self.menubar.add_cascade(label=tr("Etikedoj"), menu=m)

        m = tk.Menu(self.menubar, tearoff=0)
        m.add_checkbutton(label=tr("cx → ĉ dum skribado (Retropaŝo malfaras)"), variable=self.auto_cx,
                          command=self._update_status)
        m.add_checkbutton(label=tr("Aŭtomata linifaldo"), variable=self.wrap, command=self._toggle_wrap)
        m.add_checkbutton(label=tr("Kolorigi etikedojn"), variable=self.highlight_on, command=lambda: [self._schedule_highlight(d) for d in self.docs])
        m.add_separator()
        self._add_cmd(m, "opcioj.klavoj")
        lm = tk.Menu(m, tearoff=0)
        self._lang_var = tk.StringVar(value=CURRENT_LANG)
        for code, nomo in available_languages():
            lm.add_radiobutton(label=f"{nomo}  ({code})", value=code, variable=self._lang_var,
                               command=lambda c=code: self.set_language(c))
        m.add_cascade(label=tr("Lingvo"), menu=lm)
        self.menubar.add_cascade(label=tr("Opcioj"), menu=m)

        self.plugin_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=tr("Kromprogramoj"), menu=self.plugin_menu)

        m = tk.Menu(self.menubar, tearoff=0)
        m.add_command(label=tr("Pri la programo…"), command=self.about)
        self.menubar.add_cascade(label=tr("Helpo"), menu=m)

    # ---------------------------------------------------------------- plugin
    def load_plugins(self):
        self.plugins = []
        self.plugin_errors = []
        self.commands = {k: v for k, v in self.commands.items() if not k.startswith("plugin:")}
        self._menu_entries = {k: v for k, v in self._menu_entries.items() if not k.startswith("plugin:")}
        try:
            importlib.reload(mc)
        except Exception:
            pass
        if not os.path.isdir(PLUGIN_DIR):
            return
        for fn in sorted(os.listdir(PLUGIN_DIR)):
            if not fn.endswith(".py") or fn.startswith("_"):
                continue
            path = os.path.join(PLUGIN_DIR, fn)
            try:
                spec = importlib.util.spec_from_file_location("monato_plugin_" + fn[:-3], path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                category = getattr(mod, "CATEGORY", "Altro")
                actions = getattr(mod, "ACTIONS", None)
                if actions is None:
                    actions = [(mod.NAME, mod.run)]
                hot = {}                 # funzione -> sequenza Tk predefinita
                for seq, func in getattr(mod, "HOTKEYS", {}).items():
                    hot.setdefault(func, seq)
                used = set()
                for act in actions:
                    label, func = act[0], act[1]
                    cid = f"plugin:{fn}:{label}"
                    self._register(cid, category, label,
                                   lambda f=func, l=label: self.run_plugin(f, l), hot.get(func))
                    used.add(func)
                    self.plugins.append((category, label, func, cid))
                for func, seq in hot.items():      # tasti senza voce di menu
                    if func not in used:
                        name = getattr(func, "__name__", "funkcio")
                        label = f"{fn}: {name}"
                        self._register(f"plugin:{fn}:{name}", category, label,
                                       lambda f=func, l=label: self.run_plugin(f, l), seq)
            except Exception as e:  # un plugin rotto non deve fermare l'editor
                self.plugin_errors.append((fn, e))

    def _build_plugin_menu(self):
        m = self.plugin_menu
        m.delete(0, "end")
        cats = {}
        for cat, label, func, cid in self.plugins:
            cats.setdefault(cat, []).append(cid)
        ordered = [c for c in CATEGORY_ORDER if c in cats] + \
                  sorted(c for c in cats if c not in CATEGORY_ORDER)
        for cat in ordered:
            sub = tk.Menu(m, tearoff=0)
            for cid in cats[cat]:
                self._add_cmd(sub, cid)
            m.add_cascade(label=tr(cat), menu=sub)
        for fn, err in self.plugin_errors:
            m.add_command(label=tr("⚠ {fn}: eraro").format(fn=fn), command=lambda f=fn, e=err: show_error(
                self.root, tr("Ne eblas ŝargi la kromprogramon {f}:\n\n{e}").format(f=f, e=e)))
        m.add_separator()
        m.add_command(label=tr("Reŝargi kromprogramojn"), command=self.reload_plugins)
        m.add_command(label=tr("Malfermi la dosierujon de kromprogramoj"), command=self.open_plugin_dir)
        self._refresh_accelerators()

    def open_plugin_dir(self):
        os.makedirs(PLUGIN_DIR, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(PLUGIN_DIR)                      # noqa: S606
            elif sys.platform == "darwin":
                os.system(f'open "{PLUGIN_DIR}"')
            else:
                os.system(f'xdg-open "{PLUGIN_DIR}" >/dev/null 2>&1 &')
        except Exception as e:
            show_error(self.root, tr("Ne eblas malfermi la dosierujon:\n{dir}\n\n{e}").format(dir=PLUGIN_DIR, e=e))

    def about(self):
        show_info(self.root,
                  tr("{app} {versio}\n\n"
                     "UTF-8-redaktilo kun kromprogramoj por Esperanto kaj la teknikaj konvencioj de Monato.\n\n"
                     "Dosierujo de kromprogramoj:\n{dir}\n\n"
                     "Nova kromprogramo = nova .py-dosiero en tiu dosierujo, poste "
                     "Kromprogramoj → Reŝargi kromprogramojn.\n\n"
                     "Lingvaj pakaĵoj: {lingvoj}\n\n"
                     "Licenco: vidu LICENCO.txt").format(app=APP_NAME, versio=VERSION, dir=PLUGIN_DIR,
                                                         lingvoj=LANG_DIR), title="Pri la programo")

    def set_language(self, code):
        data = load_settings()
        data["lingvo"] = code
        try:
            save_settings(data)
        except OSError as e:
            show_error(self.root, tr("Ne eblas konservi:\n{e}").format(e=e))
            return
        load_language(code)
        show_info(self.root, tr("La lingvo estos ŝanĝita post restarto de Redaktilo."))

    def reload_plugins(self):
        self.load_plugins()
        self._build_plugin_menu()
        self._apply_bindings()
        self.set_status_message(tr("{n} funkcioj de kromprogramoj ŝargitaj").format(n=len(self.plugins)))

    def _populate_recent_menu(self):
        self.recent_menu.delete(0, "end")
        if not self.recent_files:
            self.recent_menu.add_command(label=tr("(neniu)"), state="disabled")
            return

        for path in self.recent_files:
            self.recent_menu.add_command(
                label=path,
                command=lambda p=path: self.open_file(p),
            )
        self.recent_menu.add_separator()
        self.recent_menu.add_command(
            label=tr("Forigi liston"),
            command=self._clear_recent_files,
        )

    def _remember_recent(self, path):
        if not path:
            return
        path = os.path.abspath(path)
        key = os.path.normcase(path)
        self.recent_files = [p for p in self.recent_files if os.path.normcase(p) != key]
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:10]

        settings = load_settings()
        settings["lastatempaj_dosieroj"] = self.recent_files
        try:
            save_settings(settings)
        except OSError as e:
            show_error(self.root, tr("Ne eblas konservi:\n{e}").format(e=e))

    def _clear_recent_files(self):
        self.recent_files = []
        settings = load_settings()
        settings["lastatempaj_dosieroj"] = []
        try:
            save_settings(settings)
        except OSError as e:
            show_error(self.root, tr("Ne eblas konservi:\n{e}").format(e=e))
        self._populate_recent_menu()

    # ------------------------------------------------- gestore delle klavkombinoj
    def _register(self, cid, group, label, run, default):
        self.commands[cid] = {"group": tr(group), "label": tr(label), "run": run, "default": default}

    def _register_builtin_commands(self):
        r = self._register
        r("dosiero.nova", "Dosiero", "Nova", self.new_file, "<Control-n>")
        r("dosiero.malfermi", "Dosiero", "Malfermi…", self.open_dialog, "<Control-o>")
        r("dosiero.konservi", "Dosiero", "Konservi", self.save, "<Control-s>")
        r("dosiero.konservi_kiel", "Dosiero", "Konservi kiel…", self.save_as, "<Control-S>")
        r("dosiero.fermi", "Dosiero", "Fermi la dokumenton", lambda: self.close_document(), "<Control-w>")
        r("dosiero.sekva", "Dosiero", "Sekva dokumento", lambda: self.next_document(1), "<Control-Next>")
        r("dosiero.antaua", "Dosiero", "Antaŭa dokumento", lambda: self.next_document(-1), "<Control-Prior>")
        r("dosiero.eliri", "Dosiero", "Eliri", self.quit, None)
        r("redakti.refari", "Redakti", "Refari", lambda: self._undo(True), "<Control-y>")
        r("redakti.elekti", "Redakti", "Elekti ĉion", self.select_all, "<Control-a>")
        r("redakti.serci", "Redakti", "Serĉi kaj anstataŭigi…", self.find_dialog, "<Control-f>")
        r("redakti.sekva", "Redakti", "Serĉi sekvan", lambda: self.find_next(False), None)
        r("redakti.antaua", "Redakti", "Serĉi antaŭan", lambda: self.find_next(True), None)
        r("redakti.iri", "Redakti", "Iri al linio…", self.goto_dialog, "<Control-g>")
        for label, tag, _acc, seq in TAG_MENU:
            r("etikedo." + tag, "Etikedoj", label, lambda tg=tag: self.wrap_tag(tg), seq)
        r("opcioj.klavoj", "Opcioj", "Klavkombinoj…", self.shortcuts_dialog, None)

    def key_of(self, cid):
        """Sequenza Tk attiva per il comando (scelta dell'utente o predefinita)."""
        if cid in self.user_keys:
            return self.user_keys[cid] or None
        return self.commands[cid]["default"]

    def _add_cmd(self, menu, cid):
        c = self.commands[cid]
        menu.add_command(label=c["label"], command=c["run"],
                         accelerator=seq_to_display(self.key_of(cid)))
        self._menu_entries.setdefault(cid, []).append((menu, menu.index("end")))

    def _refresh_accelerators(self):
        for cid, entries in self._menu_entries.items():
            if cid not in self.commands:
                continue
            acc = seq_to_display(self.key_of(cid))
            for menu, idx in entries:
                try:
                    menu.entryconfigure(idx, accelerator=acc)
                except tk.TclError:
                    pass

    def _apply_bindings(self):
        for w, seq in self._bound:
            try:
                w.unbind(seq)
            except tk.TclError:
                pass
        self._bound = []
        for cid, c in self.commands.items():
            seq = self.key_of(cid)
            if not seq:
                continue
            for w in [d.text for d in self.docs] + [self.root]:
                try:
                    w.bind(seq, lambda e, f=c["run"]: (f(), "break")[1])
                    self._bound.append((w, seq))
                except tk.TclError:
                    break              # sequenza non valida nel file: ignorata
        self._refresh_accelerators()

    def _store_key(self, cid, seq):
        if seq == self.commands[cid]["default"]:
            self.user_keys.pop(cid, None)
        else:
            self.user_keys[cid] = seq or ""
        try:
            save_user_keys(self.user_keys)
        except OSError as e:
            show_error(self.root, tr("Ne eblas konservi la klavkombinojn:\n{dosiero}\n\n{e}").format(dosiero=KEYS_FILE, e=e))
        self._apply_bindings()

    def set_key(self, cid, seq, parent=None):
        """Assegna una combinazione (gestendo i conflitti). True se applicata."""
        if seq:
            for other, oc in self.commands.items():
                if other != cid and self.key_of(other) == seq:
                    if not yes_no(parent or self.root,
                                  tr("«{klavo}» jam apartenas al «{nomo}».\nĈu transpreni la klavon?")
                                  .format(klavo=seq_to_display(seq), nomo=oc["label"])):
                        return False
                    self._store_key(other, None)
        self._store_key(cid, seq)
        return True

    def _capture_key(self, parent, label):
        """Finestra che attende la pressione di una combinazione. -> ('set', seq) / ('clear',) / None"""
        res = {"v": None}
        d = tk.Toplevel(parent)
        d.title(tr("Nova klavkombino"))
        d.transient(parent)
        d.resizable(False, False)
        tk.Label(d, text=tr("Funkcio: {nomo}").format(nomo=label),
                 font=("TkDefaultFont", 10, "bold")).pack(padx=16, pady=(14, 4))
        tk.Label(d, text=tr("Premu la novan klavkombinon\n(Ctrl/Alt + klavo, aŭ funkcia klavo F1–F12).\nEsc = nuligi"),
                 justify="center").pack(padx=16, pady=4)
        shown = tk.StringVar(value="—")
        tk.Label(d, textvariable=shown, font=("TkDefaultFont", 14), width=24,
                 relief="sunken", pady=6).pack(padx=16, pady=8)
        cur = {"seq": None}

        def on_key(ev):
            if ev.keysym == "Escape":
                d.destroy()
                return "break"
            seq = event_to_seq(ev)
            if seq:
                cur["seq"] = seq
                shown.set(seq_to_display(seq))
            return "break"

        def ok():
            if cur["seq"]:
                res["v"] = ("set", cur["seq"])
            d.destroy()

        def clear():
            res["v"] = ("clear",)
            d.destroy()

        bf = tk.Frame(d)
        bf.pack(pady=(4, 14))
        tk.Button(bf, text=tr("Bone"), width=10, command=ok).pack(side="left", padx=4)
        tk.Button(bf, text=tr("Forigi klavon"), width=14, command=clear).pack(side="left", padx=4)
        tk.Button(bf, text=tr("Nuligi"), width=10, command=d.destroy).pack(side="left", padx=4)
        d.bind("<KeyPress>", on_key)
        d.bind("<Return>", lambda e: ok())
        d.update_idletasks()
        d.grab_set()
        d.focus_force()
        d.wait_window()
        return res["v"]

    def shortcuts_dialog(self):
        d = tk.Toplevel(self.root)
        d.title(tr("Klavkombinoj"))
        d.geometry("640x480")
        d.transient(self.root)

        top = tk.Frame(d)
        top.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(top, text=tr("Serĉi:")).pack(side="left")
        filt = tk.StringVar()
        ent = tk.Entry(top, textvariable=filt)
        ent.pack(side="left", fill="x", expand=True, padx=6)

        mid = tk.Frame(d)
        mid.pack(fill="both", expand=True, padx=8, pady=4)
        tree = ttk.Treeview(mid, columns=("grupo", "funkcio", "klavo"), show="headings", selectmode="browse")
        tree.heading("grupo", text=tr("Grupo"))
        tree.heading("funkcio", text=tr("Funkcio"))
        tree.heading("klavo", text=tr("Klavkombino"))
        tree.column("grupo", width=110, stretch=False)
        tree.column("funkcio", width=320)
        tree.column("klavo", width=150, stretch=False)
        sb = ttk.Scrollbar(mid, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        note = tk.Label(d, anchor="w", fg="#555",
                        text=tr("Duoble alklaku aŭ premu Enter por ŝanĝi. La elekto estas konservata aŭtomate."))
        note.pack(fill="x", padx=8)

        def groups_order():
            builtin = [tr(x) for x in ("Dosiero", "Redakti", "Etikedoj", "Opcioj")]
            others = sorted({c["group"] for c in self.commands.values()} - set(builtin))
            return builtin + others

        def refresh(select=None):
            tree.delete(*tree.get_children())
            q = filt.get().strip().lower()
            for g in groups_order():
                for cid, c in self.commands.items():
                    if c["group"] != g:
                        continue
                    key = seq_to_display(self.key_of(cid))
                    if q and q not in (g + " " + c["label"] + " " + key).lower():
                        continue
                    tree.insert("", "end", iid=cid, values=(g, c["label"], key))
            if select and tree.exists(select):
                tree.selection_set(select)
                tree.see(select)

        def current():
            sel = tree.selection()
            return sel[0] if sel else None

        def change(_e=None):
            cid = current()
            if not cid:
                return "break"
            r = self._capture_key(d, self.commands[cid]["label"])
            if r:
                self.set_key(cid, r[1] if r[0] == "set" else None, parent=d)
                refresh(cid)
            return "break"

        def remove():
            cid = current()
            if cid:
                self._store_key(cid, None)
                refresh(cid)

        def default():
            cid = current()
            if cid:
                self.user_keys.pop(cid, None)
                self.set_key(cid, self.commands[cid]["default"], parent=d)
                refresh(cid)

        def reset_all():
            if yes_no(d, "Ĉu restarigi ĉiujn klavkombinojn al la komencaj valoroj?"):
                self.user_keys = {}
                self._store_key_all()
                refresh()

        bf = tk.Frame(d)
        bf.pack(fill="x", padx=8, pady=8)
        tk.Button(bf, text=tr("Ŝanĝi…"), command=change).pack(side="left", padx=2)
        tk.Button(bf, text=tr("Forigi klavon"), command=remove).pack(side="left", padx=2)
        tk.Button(bf, text=tr("Komenca valoro"), command=default).pack(side="left", padx=2)
        tk.Button(bf, text=tr("Restarigi ĉiujn"), command=reset_all).pack(side="left", padx=2)
        tk.Button(bf, text=tr("Fermi"), width=10, command=d.destroy).pack(side="right", padx=2)

        tree.bind("<Double-Button-1>", change)
        tree.bind("<Return>", change)
        filt.trace_add("write", lambda *a: refresh())
        d.bind("<Escape>", lambda e: d.destroy())
        refresh()
        ent.focus_set()

    def _store_key_all(self):
        try:
            save_user_keys(self.user_keys)
        except OSError as e:
            show_error(self.root, tr("Ne eblas konservi la klavkombinojn:\n{dosiero}\n\n{e}").format(dosiero=KEYS_FILE, e=e))
        self._apply_bindings()

    def run_plugin(self, func, label):
        try:
            func(self.ctx)
        except Exception:
            tb = traceback.format_exc()
            show_error(self.root, tr("Eraro en la kromprogramo «{label}»:\n\n{tb}").format(label=label, tb=tb[-1500:]))
        self.text.focus_set()

    # --------------------------------------------------------------- tasti
    def _bind_text(self, doc):
        t = doc.text
        t.bind("<KeyPress-x>", self._on_x)
        t.bind("<KeyPress-X>", self._on_x)
        t.bind("<KeyPress-BackSpace>", self._on_backspace)
        t.bind("<Key>", self._on_any_key)
        t.bind("<<Modified>>", lambda e, d=doc: self._on_modified(d))
        t.bind("<Configure>", lambda e, d=doc: self._redraw_gutter(d))
        t.bind("<KeyRelease>", lambda e: self._on_cursor_move())
        t.bind("<ButtonRelease-1>", lambda e: self._on_cursor_move())
        t.configure(yscrollcommand=lambda *a, d=doc: self._on_yscroll(d, *a))

    # ------------------------------------------------------------ documenti
    def _add_document(self):
        doc = Document(self, self.nb)
        self.docs.append(doc)
        self._doc_by_tab[str(doc.frame)] = doc
        self.nb.add(doc.frame, text=doc.display_name())
        self._bind_text(doc)
        self._apply_bindings()              # collega i tasti anche al nuovo testo
        self.nb.select(doc.frame)
        self._on_tab_changed()
        return doc

    def _select_doc(self, doc):
        self.nb.select(doc.frame)
        self._on_tab_changed()

    def _on_tab_changed(self):
        doc = self.doc
        if doc is None:
            return
        self._status_msg = ""
        self._sync_report(doc)
        self._update_title()
        self._update_status()
        doc.text.focus_set()
        self.root.after_idle(lambda d=doc: self._redraw_gutter(d))

    def _update_tab(self, doc):
        try:
            self.nb.tab(doc.frame, text=("*" if doc.dirty else "") + doc.display_name())
        except tk.TclError:
            pass

    def close_document(self, doc=None):
        """Chiude una scheda (chiede di salvare se serve). False se annullato."""
        doc = doc or self.doc
        if doc.dirty:
            self._select_doc(doc)
            if not self._confirm_discard():
                return False
        if doc._hl_job:
            try:
                self.root.after_cancel(doc._hl_job)
            except tk.TclError:
                pass
        self.nb.forget(doc.frame)
        self.docs.remove(doc)
        self._doc_by_tab.pop(str(doc.frame), None)
        doc.frame.destroy()
        self._bound = [(w, q) for w, q in self._bound if w is not doc.text]
        if not self.docs:
            self._add_document()
        else:
            self._on_tab_changed()
        return True

    def next_document(self, step=1):
        if len(self.docs) > 1:
            i = self.docs.index(self.doc)
            self._select_doc(self.docs[(i + step) % len(self.docs)])

    def _tab_at(self, event):
        try:
            idx = self.nb.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return None
        return self.docs[idx] if 0 <= idx < len(self.docs) else None

    def _tab_popup(self, event):
        doc = self._tab_at(event)
        if doc is None:
            return
        self._select_doc(doc)
        m = self._tab_menu
        m.delete(0, "end")
        m.add_command(label=tr("Konservi"), command=self.save)
        m.add_command(label=tr("Fermi la dokumenton"), command=lambda d=doc: self.close_document(d))
        m.tk_popup(event.x_root, event.y_root)

    def _tab_middle_click(self, event):
        doc = self._tab_at(event)
        if doc is not None:
            self.close_document(doc)

    # ---- cx → ĉ durante la digitazione
    def _on_x(self, event):
        if not self.auto_cx.get() or self.text.tag_ranges("sel"):
            self._last_conv = None
            return None
        prev = self.text.get("insert-1c", "insert")
        if prev in X_MAP:
            self.text.delete("insert-1c", "insert")
            self.text.insert("insert", X_MAP[prev])
            self._last_conv = (self.text.index("insert"), prev + event.char)
            return "break"
        self._last_conv = None
        return None

    def _on_backspace(self, event):
        lc = self._last_conv
        self._last_conv = None
        if lc and not self.text.tag_ranges("sel") and self.text.index("insert") == lc[0]:
            self.text.delete("insert-1c", "insert")
            self.text.insert("insert", lc[1])
            return "break"
        return None

    def _on_any_key(self, event):
        if event.keysym not in ("Shift_L", "Shift_R", "Control_L", "Control_R",
                                "Alt_L", "Alt_R", "Caps_Lock", "x", "X", "BackSpace"):
            self._last_conv = None

    # ---------------------------------------------------------------- testo
    def get_text(self):
        return self.text.get("1.0", "end-1c")

    def _undo_group(self, fn):
        """Esegue fn() come un'unica operazione annullabile con un solo Ctrl+Z."""
        t = self.text
        t.edit_separator()
        t.configure(autoseparators=False)
        try:
            fn()
        finally:
            t.edit_separator()
            t.configure(autoseparators=True)

    def set_text(self, s):
        """Sostituisce tutto il testo; l'operazione si annulla con un solo Ctrl+Z."""
        t = self.text
        yview = t.yview()[0]

        def op():
            t.delete("1.0", "end")
            t.insert("1.0", s)

        self._undo_group(op)
        t.mark_set("insert", "1.0")
        t.yview_moveto(yview)
        self._schedule_highlight()

    def get_selection(self):
        if self.text.tag_ranges("sel"):
            return self.text.get("sel.first", "sel.last")
        return None

    def replace_selection(self, s):
        t = self.text
        if not t.tag_ranges("sel"):
            t.insert("insert", s)
            return
        start = t.index("sel.first")

        def op():
            t.delete("sel.first", "sel.last")
            t.insert(start, s)

        self._undo_group(op)
        t.tag_add("sel", start, f"{start}+{len(s)}c")

    def replace_range(self, a, b, s):
        t = self.text

        def op():
            t.delete(a, b)
            t.insert(a, s)

        self._undo_group(op)

    def wrap_tag(self, tag):
        t = self.text
        if tag == "!--":
            op, cl = "<!-- ", " -->"
        else:
            op, cl = f"<{tag}>", f"</{tag}>"
        if t.tag_ranges("sel"):
            s = t.get("sel.first", "sel.last")
            self.replace_selection(op + s + cl)
        else:
            t.insert("insert", op + cl)
            t.mark_set("insert", f"insert-{len(cl)}c")
        t.focus_set()

    def select_all(self):
        self.text.tag_add("sel", "1.0", "end-1c")
        self.text.mark_set("insert", "end-1c")

    def _undo(self, redo):
        try:
            (self.text.edit_redo if redo else self.text.edit_undo)()
        except tk.TclError:
            pass
        self._schedule_highlight()

    def _toggle_wrap(self):
        for d in self.docs:
            d.text.configure(wrap="word" if self.wrap.get() else "none")
            self._redraw_gutter(d)

    # --------------------------------------------------------------- file
    def _confirm_discard(self):
        """Per il documento corrente."""
        if not self.dirty:
            return True
        ans = yes_no_cancel(self.root, "La dokumento havas nekonservitajn ŝanĝojn.\nĈu konservi?")
        if ans is None:
            return False
        if ans:
            return self.save()
        return True

    def new_file(self):
        self._add_document()

    def open_dialog(self):
        ps = filedialog.askopenfilenames(
            parent=self.root, title=tr("Malfermi"),
            filetypes=[(tr("Tekstoj kaj Monato"), "*.txt *.xml *.monato"), (tr("Ĉiuj dosieroj"), "*.*")])
        if isinstance(ps, str):
            ps = self.root.tk.splitlist(ps)
        for p in ps:
            self._open_path(p)

    def open_file(self, path):
        self._open_path(path)

    def _open_path(self, path):
        key = os.path.normcase(os.path.abspath(path))
        for d in self.docs:                       # già aperto: passa a quella scheda
            if d.path and os.path.normcase(os.path.abspath(d.path)) == key:
                self._select_doc(d)
                self._remember_recent(d.path)
                return
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as e:
            show_error(self.root, tr("Ne eblas malfermi la dosieron:\n{e}").format(e=e))
            return
        note = "UTF-8"
        try:
            s = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                s = raw.decode("cp1252")
                note = "Windows-1252 (estos konservita kiel UTF-8)"
            except UnicodeDecodeError:
                s = raw.decode("latin-1")
                note = "Latin-1 (estos konservita kiel UTF-8)"
        cur = self.doc                            # scheda vuota e intatta: la riusa
        if not (cur.path is None and not cur.dirty and cur.text.get("1.0", "end-1c") == ""):
            self._add_document()
        self.eol = "\r\n" if "\r\n" in s else "\n"
        s = s.replace("\r\n", "\n")
        self._load(s, path, note)
        self._remember_recent(path)

    def _load(self, s, path, note="UTF-8"):
        t = self.text
        t.delete("1.0", "end")
        t.insert("1.0", s)
        self.root.update()          # smaltisce gli eventi <<Modified>> in coda
        t.edit_reset()
        t.edit_modified(False)
        self.root.update()
        self.dirty = False
        t.mark_set("insert", "1.0")
        t.see("1.0")
        self.path = path
        self.encoding_note = note
        if path is None:
            self.eol = "\n"
        self.hide_report()
        self._schedule_highlight()
        self._update_title()
        self._update_status()

    def save(self):
        if not self.path:
            return self.save_as()
        return self._write(self.path)

    def save_as(self):
        p = filedialog.asksaveasfilename(
            parent=self.root, title=tr("Konservi kiel"), defaultextension=".xml",
            initialfile=os.path.basename(self.path) if self.path else "",
            filetypes=[(tr("XML de Monato"), "*.xml"), (tr("Teksto"), "*.txt"), (tr("Ĉiuj dosieroj"), "*.*")])
        if not p:
            return False
        return self._write(p)

    def _write(self, path):
        data = self.get_text().replace("\n", self.eol)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(data)
        except OSError as e:
            show_error(self.root, tr("Ne eblas konservi:\n{e}").format(e=e))
            return False
        self.path = path
        self._remember_recent(path)
        self.encoding_note = "UTF-8"
        self.dirty = False
        self._update_title()
        self._update_status()
        return True

    def quit(self):
        for d in list(self.docs):
            if d.dirty:
                self._select_doc(d)
                if not self._confirm_discard():
                    return
        self.root.destroy()

    # -------------------------------------------------------- pannello report
    def show_report(self, title, items):
        """Risultati del plugin: restano legati al documento su cui sono stati prodotti."""
        doc = self.doc
        doc._report_lines = []
        doc._report_items = []
        doc._report_title = title
        entries = []
        for it in items:
            if isinstance(it, (tuple, list)):
                line, msg = it[0], it[1]
                entries.append(tr("linio {line}: {msg}").format(line=line, msg=tr(str(msg))))
                doc._report_lines.append(line)
                doc._report_items.append((line, tr(str(msg))))
            else:
                entries.append(tr(str(it)))
                doc._report_lines.append(None)
                doc._report_items.append((None, tr(str(it))))
        doc._report_entries = entries
        self._sync_report(doc)
        self._redraw_gutter(doc)

    def _sync_report(self, doc):
        """Mostra nel pannello i risultati del documento (o nasconde il pannello)."""
        self.report_list.delete(0, "end")
        if doc._report_entries is None:
            self.panel.pack_forget()
            return
        for e in doc._report_entries:
            self.report_list.insert("end", e)
        self.panel_title.config(text=doc._report_title)
        self.panel.pack(side="bottom", fill="x", before=self.main)
        if doc._report_lines:
            self.report_list.selection_set(0)
            self.report_list.activate(0)

    def hide_report(self):
        doc = self.doc
        doc._report_entries = None
        doc._report_lines = []
        doc._report_items = []
        self.panel.pack_forget()
        self.text.tag_remove("hit", "1.0", "end")
        self.text.focus_set()

    def _report_jump(self, _event=None):
        sel = self.report_list.curselection()
        if not sel:
            return
        line = self._report_lines[sel[0]]
        if line:
            self.goto_line(line)

    # ---- esportazione dei risultati dei plugin
    def _to_clipboard(self, text, n):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()                  # il contenuto resta disponibile anche dopo la chiusura
        self.set_status_message(tr("{n} linioj kopiitaj al la tondejo").format(n=n))

    def report_copy_selected(self):
        sel = self.report_list.curselection()
        if not sel:
            return self.report_copy_all()
        lines = [self.report_list.get(i) for i in sel]
        self._to_clipboard("\n".join(lines), len(lines))

    def report_copy_all(self):
        lines = list(self.report_list.get(0, "end"))
        if lines:
            self._to_clipboard("\n".join(lines), len(lines))

    def report_select_all(self):
        self.report_list.selection_set(0, "end")

    def _report_popup(self, event):
        i = self.report_list.nearest(event.y)
        if i >= 0 and not self.report_list.selection_includes(i):
            self.report_list.selection_clear(0, "end")
            self.report_list.selection_set(i)
        self._report_menu.tk_popup(event.x_root, event.y_root)

    def report_save(self):
        """Salva tutti i risultati: .txt (una voce per riga) oppure .csv (apribile in Excel)."""
        if not self._report_items:
            return
        base = os.path.splitext(os.path.basename(self.path))[0] if self.path else "rezulto"
        slug = re.sub(r"[^\w]+", "_", self._report_title.split(":")[0]).strip("_") or "rezulto"
        p = filedialog.asksaveasfilename(
            parent=self.root, title=tr("Konservi rezulton"), defaultextension=".txt",
            initialfile=f"{base}_{slug}.txt",
            filetypes=[(tr("Teksto (.txt)"), "*.txt"), (tr("CSV por Excel (.csv)"), "*.csv"),
                       (tr("Ĉiuj dosieroj"), "*.*")])
        if not p:
            return
        try:
            if p.lower().endswith(".csv"):
                with open(p, "w", encoding="utf-8-sig", newline="") as f:     # BOM: Excel legas ĉapelitajn literojn
                    w = csv.writer(f, delimiter=";")
                    w.writerow([tr("linio"), tr("mesaĝo")])
                    for line, msg in self._report_items:
                        w.writerow(["" if line is None else line, msg])
            else:
                head = [self._report_title]
                if self.path:
                    head.append(tr("Dosiero: {nomo}").format(nomo=os.path.basename(self.path)))
                body = [self.report_list.get(i) for i in range(self.report_list.size())]
                with open(p, "w", encoding="utf-8") as f:
                    f.write("\n".join(head + [""] + body) + "\n")
        except OSError as e:
            show_error(self.root, tr("Ne eblas konservi:\n{e}").format(e=e))
            return
        self.set_status_message(tr("Rezulto konservita: {nomo}").format(nomo=os.path.basename(p)))

    def goto_line(self, line):
        t = self.text
        t.tag_remove("hit", "1.0", "end")
        t.mark_set("insert", f"{line}.0")
        t.see(f"{line}.0")
        t.tag_add("hit", f"{line}.0", f"{line}.end+1c")
        t.focus_set()

    def goto_dialog(self):
        v = ask_text(self.root, "Iri al linio:")
        if v and v.strip().isdigit() and int(v) > 0:
            self.goto_line(int(v))

    # ----------------------------------------------------------------- cerca
    def find_dialog(self):
        if getattr(self, "_fd", None) and self._fd.winfo_exists():
            self._fd.lift()
            self._fd.focus_force()
            return
        d = tk.Toplevel(self.root)
        d.title(tr("Serĉi kaj anstataŭigi"))
        d.transient(self.root)
        d.resizable(False, False)
        self._fd = d
        if not hasattr(self, "_find_var"):                 # le impostazioni restano tra un'apertura e l'altra
            self._find_var = tk.StringVar()
            self._repl_var = tk.StringVar()
            self._case_var = tk.BooleanVar(value=False)
            self._regex_var = tk.BooleanVar(value=False)
            self._esc_var = tk.BooleanVar(value=True)
        sel = self.get_selection()
        if sel and "\n" not in sel:
            self._find_var.set(sel)

        ttk.Label(d, text=tr("Serĉi:")).grid(row=0, column=0, padx=6, pady=4, sticky="e")
        e1 = ttk.Entry(d, textvariable=self._find_var, width=40)
        e1.grid(row=0, column=1, columnspan=3, padx=6, pady=4)
        ttk.Label(d, text=tr("Anstataŭigi per:")).grid(row=1, column=0, padx=6, pady=4, sticky="e")
        ttk.Entry(d, textvariable=self._repl_var, width=40).grid(row=1, column=1, columnspan=3, padx=6)
        ttk.Checkbutton(d, text=tr("Distingi majusklojn"), variable=self._case_var).grid(
            row=2, column=1, columnspan=3, sticky="w", padx=6, pady=(4, 0))
        ttk.Checkbutton(d, text=tr("Regulaj esprimoj"), variable=self._regex_var).grid(
            row=3, column=1, columnspan=3, sticky="w", padx=6)
        ttk.Checkbutton(d, text=tr("Specialaj signoj  (\\n  \\t  \\uXXXX)"), variable=self._esc_var).grid(
            row=4, column=1, columnspan=3, sticky="w", padx=6)
        ttk.Checkbutton(d, text=tr("Serĉi en ĉiuj folioj"), variable=self.search_all).grid(
            row=5, column=1, columnspan=3, sticky="w", padx=6)
        ttk.Button(d, text=tr("Serĉi antaŭen"), command=lambda: self.find_next(False)).grid(row=6, column=1, pady=(8, 2))
        ttk.Button(d, text=tr("Serĉi malantaŭen"), command=lambda: self.find_next(True)).grid(row=6, column=2)
        ttk.Button(d, text=tr("Anstataŭigi"), command=self.replace_one).grid(row=6, column=3, padx=2)
        ttk.Button(d, text=tr("Helpo"), command=lambda: show_info(self.root, tr(SEARCH_HELP), title="Serĉi: helpo")
                   ).grid(row=7, column=1, pady=(0, 8))
        ttk.Button(d, text=tr("Anstataŭigi ĉion"), command=self.replace_all).grid(row=7, column=3, padx=2, pady=(0, 8))
        e1.focus_set()
        e1.bind("<Return>", lambda e: self.find_next(False))
        d.bind("<Escape>", lambda e: d.destroy())

    def _compile_search(self):
        """(regex, espandi) dalle impostazioni della finestra, oppure None con messaggio d'errore."""
        pat = self._find_var.get()
        if not pat:
            return None
        try:
            return build_search(pat, self._repl_var.get(), self._regex_var.get(),
                                self._esc_var.get(), self._case_var.get())
        except re.error as e:
            show_error(self.root, tr("Nevalida regula esprimo:\n{e}").format(e=e))
            return None

    def _offset(self, index):
        return len(self.text.get("1.0", index))

    def _find_next_local(self, backwards=False):
        comp = self._compile_search()
        if comp is None:
            return False
        rx, _ = comp
        t = self.text
        text = self.get_text()
        if t.tag_ranges("sel"):
            s0, s1 = self._offset("sel.first"), self._offset("sel.last")
        else:
            s0 = s1 = self._offset("insert")

        def nonempty(it):
            return (m for m in it if m.end() > m.start())

        wrapped = False
        if not backwards:
            m = next(nonempty(rx.finditer(text, s1)), None)
            if m is None:
                m = next((x for x in nonempty(rx.finditer(text, 0)) if x.start() < max(s1, 1)), None)
                wrapped = m is not None
        else:
            m = None
            for x in nonempty(rx.finditer(text)):
                if x.start() < s0:
                    m = x
                else:
                    break
            if m is None:
                for x in nonempty(rx.finditer(text)):
                    m = x
                wrapped = m is not None
        if m is None:
            self.set_status_message(tr("Ne trovita"))
            return False
        a, b = f"1.0+{m.start()}c", f"1.0+{m.end()}c"
        t.tag_remove("sel", "1.0", "end")
        t.tag_add("sel", a, b)
        t.mark_set("insert", a if backwards else b)
        t.see(a)
        if wrapped:
            self.set_status_message(tr("Daŭrigita de la fino") if backwards else tr("Daŭrigita de la komenco"))
        return True

    def find_next(self, backwards=False):
        if self.search_all.get():
            docs = self.docs
            start = docs.index(self.doc) if self.doc in docs else 0
            for step in range(len(docs)):
                doc = docs[(start + step) % len(docs)]
                self._select_doc(doc)
                if self._find_next_local(backwards):
                    return True
            self.set_status_message(tr("Ne trovita"))
            return False
        return self._find_next_local(backwards)

    def _replace_one_local(self):
        comp = self._compile_search()
        if comp is None:
            return False
        rx, expand = comp
        if self.text.tag_ranges("sel"):
            s0, s1 = self._offset("sel.first"), self._offset("sel.last")
            m = rx.match(self.get_text(), s0)
            if m and m.end() == s1 and s1 > s0:
                try:
                    new = expand(m)
                except (re.error, IndexError) as e:
                    show_error(self.root, tr("Nevalida anstataŭigo:\n{e}").format(e=e))
                    return False
                self.replace_selection(new)
                self._find_next_local(False)
                return True
        return False

    def replace_one(self):
        if self.search_all.get():
            docs = self.docs
            start = docs.index(self.doc) if self.doc in docs else 0
            for step in range(len(docs)):
                doc = docs[(start + step) % len(docs)]
                self._select_doc(doc)
                if self._replace_one_local():
                    return
            self.set_status_message(tr("Ne trovita"))
            return
        self._replace_one_local()

    def _replace_all_local(self):
        comp = self._compile_search()
        if comp is None:
            return 0
        rx, expand = comp
        try:
            new, n = rx.subn(expand, self.get_text())
        except (re.error, IndexError) as e:
            show_error(self.root, tr("Nevalida anstataŭigo:\n{e}").format(e=e))
            return 0
        if n and new != self.get_text():
            self.set_text(new)
        return n

    def replace_all(self):
        if self.search_all.get():
            total = 0
            for doc in self.docs:
                self._select_doc(doc)
                total += self._replace_all_local()
            self.set_status_message(tr("{n} anstataŭigoj").format(n=total))
            return
        total = self._replace_all_local()
        self.set_status_message(tr("{n} anstataŭigoj").format(n=total))

    # ------------------------------------------------- evidenziazione / stato
    def _schedule_highlight(self, doc=None):
        doc = doc or self.doc
        if doc._hl_job:
            self.root.after_cancel(doc._hl_job)
        doc._hl_job = self.root.after(150, lambda: self._highlight(doc))

    def _highlight(self, doc):
        doc._hl_job = None
        if doc not in self.docs:
            return
        t = doc.text
        for name in ("tag", "unknown", "comment"):
            t.tag_remove(name, "1.0", "end")
        if not self.highlight_on.get():
            return
        s = t.get("1.0", "end-1c")
        for m in re.finditer(r"<[^>]*>", s):
            t.tag_add("tag", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in mc.TAG_RE.finditer(s):
            if m.group(2) not in mc.KNOWN_TAGS:
                t.tag_add("unknown", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        for m in mc.COMMENT_RE.finditer(s):
            t.tag_remove("tag", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
            t.tag_remove("unknown", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
            t.tag_add("comment", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        t.tag_raise("sel")

    def _on_modified(self, doc):
        # <<Modified>> scatta solo quando il flag cambia: lo riazzeriamo
        # ogni volta e teniamo un nostro flag "dirty" per documento.
        if not doc.text.edit_modified():
            return
        doc.dirty = True
        doc.text.edit_modified(False)
        self._schedule_highlight(doc)
        self._update_tab(doc)
        if doc is self.doc:
            self._update_title()
            self._update_status()
        self._redraw_gutter(doc)

    def _on_cursor_move(self):
        self.text.tag_remove("hit", "1.0", "end")
        self._status_msg = ""
        self._update_status()

    def _on_yscroll(self, doc, *a):
        doc.vsb.set(*a)
        self._redraw_gutter(doc)

    def _redraw_gutter(self, doc=None):
        doc = doc or self.doc
        if doc is None or doc not in self.docs:
            return
        g, text = doc.gutter, doc.text
        g.delete("all")
        w = int(g.cget("width"))
        i = text.index("@0,0")
        last = None
        while True:
            d = text.dlineinfo(i)
            if d is None:
                break
            ln = i.split(".")[0]
            if ln != last:
                g.create_text(w - 6, d[1], anchor="ne", text=ln, font=self.font, fill="#888")
                last = ln
            nxt = text.index(f"{i}+1line")
            if nxt == i:
                break
            i = nxt

    def _update_title(self):
        doc = self.doc
        if doc is None:
            return
        mod = "*" if doc.dirty else ""
        self.root.title(f"{mod}{doc.display_name()} — {APP_NAME}")
        self._update_tab(doc)

    def set_status_message(self, msg):
        self._status_msg = msg
        self._update_status()

    def _update_status(self):
        line, col = self.text.index("insert").split(".")
        n = len(self.get_text())
        parts = [tr("Linio {line}, kol. {col}").format(line=line, col=int(col) + 1),
                 tr("{n} signoj").format(n=n), tr(self.encoding_note),
                 tr("cx→ĉ: {stato}").format(stato=tr("jes") if self.auto_cx.get() else tr("ne"))]
        s = "   |   ".join(parts)
        if self._status_msg:
            s += "   |   " + self._status_msg
        self.status.config(text=s)


def main():
    root = tk.Tk()
    if "--proba" in sys.argv:                 # prova: carica i kromprogramoj, stampa e chiude
        app = App(root)
        print("FROZEN:", FROZEN, "| PLUGIN_DIR:", PLUGIN_DIR)
        for cat, label, _f, _cid in app.plugins:
            print("PLUGIN:", cat, "|", label)
        for fn, err in app.plugin_errors:
            print("ERARO:", fn, "->", err)
        root.destroy()
        return
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    App(root, paths)
    root.mainloop()


if __name__ == "__main__":
    main()
