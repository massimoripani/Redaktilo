#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Redaktilo: UTF-8-redaktilo kun kromprogramoj (menuo "Kromprogramoj").

Lanĉo:  python editor.py [dosiero]
La kromprogramoj estas la .py-dosieroj en la dosierujo "kromprogramoj"
(vidu kromprogramoj/_esempio.py). En la .exe-versio tiu dosierujo troviĝas apud la .exe.
"""
import importlib
import importlib.util
import os
import re
import sys
import traceback
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
VERSION = "1.0"
CATEGORY_ORDER = ["Kontrolo", "Konverto", "Teksto", "Iloj"]

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
# Dialoghi in esperanto (quelli di sistema usano la lingua di Windows)
# =====================================================================
def ask_dialog(parent, title, text, buttons, entry=None, default=0):
    """Dialogo modale. Ritorna (indice del bottone o None, testo dell'eventuale campo)."""
    d = tk.Toplevel(parent)
    d.title(title)
    d.transient(parent)
    d.resizable(False, False)
    res = {"btn": None, "text": None}
    var = tk.StringVar(value=entry or "")
    ttk.Label(d, text=text, justify="left", wraplength=480, padding=(16, 14)).pack()
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
        self._app.show_report(title, items)

    def info(self, msg):
        show_info(self._app.root, msg)

    def warn(self, msg):
        show_warn(self._app.root, msg)

    def confirm(self, msg):
        return yes_no(self._app.root, msg)

    def ask(self, msg, initial=""):
        return ask_text(self._app.root, msg, initial)

    def status(self, msg):
        self._app.set_status_message(msg)

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
# Applicazione
# =====================================================================
class App:
    def __init__(self, root, path=None):
        self.root = root
        self.path = None
        self.eol = "\n"
        self.encoding_note = "UTF-8"
        self.auto_cx = tk.BooleanVar(value=True)
        self.wrap = tk.BooleanVar(value=True)
        self.highlight_on = tk.BooleanVar(value=True)
        self._last_conv = None
        self._hl_job = None
        self.dirty = False
        self._status_msg = ""
        self.plugins = []
        self.plugin_errors = []
        self.ctx = Context(self)

        self._build_ui()
        self._build_menus()
        self.load_plugins()
        self._build_plugin_menu()
        self._bind_keys()
        self._bind_plugin_hotkeys()

        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._update_title()
        self._update_status()
        if path:
            self.open_file(path)

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

        self.gutter = tk.Canvas(self.main, width=48, highlightthickness=0, bg="#f0f0f0")
        self.gutter.pack(side="left", fill="y")

        self.vsb = ttk.Scrollbar(self.main, orient="vertical")
        self.vsb.pack(side="right", fill="y")

        self.text = tk.Text(self.main, undo=True, autoseparators=True, maxundo=-1,
                            wrap="word", font=self.font, padx=6, pady=4,
                            borderwidth=0, highlightthickness=0, spacing1=1,
                            insertwidth=2, selectbackground="#b4d5fe",
                            selectforeground="black", inactiveselectbackground="#d0d0d0")
        self.text.pack(side="left", fill="both", expand=True)
        self.vsb.configure(command=self.text.yview)
        self.text.configure(yscrollcommand=self._on_yscroll)

        self.text.tag_configure("tag", foreground="#1f5fbf")
        self.text.tag_configure("unknown", foreground="#c00000", underline=True)
        self.text.tag_configure("comment", foreground="#2e7d32", font=self._italic())
        self.text.tag_configure("hit", background="#fff2a8")
        self.text.tag_raise("sel")

        # pannello risultati (appare quando un plugin chiama ctx.report)
        self.panel = ttk.Frame(r)
        head = ttk.Frame(self.panel)
        head.pack(fill="x")
        self.panel_title = ttk.Label(head, text="", font=("TkDefaultFont", 10, "bold"))
        self.panel_title.pack(side="left", padx=6, pady=2)
        ttk.Button(head, text="✕", width=3, command=self.hide_report).pack(side="right", padx=4)
        body = ttk.Frame(self.panel)
        body.pack(fill="both", expand=True)
        self.report_list = tk.Listbox(body, height=7, activestyle="dotbox", font=self.font)
        sb = ttk.Scrollbar(body, orient="vertical", command=self.report_list.yview)
        self.report_list.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.report_list.pack(side="left", fill="both", expand=True)
        self.report_list.bind("<Double-Button-1>", self._report_jump)
        self.report_list.bind("<Return>", self._report_jump)
        self._report_lines = []

        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<Configure>", lambda e: self._redraw_gutter())
        self.text.bind("<KeyRelease>", lambda e: self._on_cursor_move())
        self.text.bind("<ButtonRelease-1>", lambda e: self._on_cursor_move())
        self.text.focus_set()

    def _italic(self):
        f = self.font.copy()
        f.configure(slant="italic")
        self._italic_font = f
        return f

    def _build_menus(self):
        r = self.root
        self.menubar = tk.Menu(r)
        r.config(menu=self.menubar)

        m = tk.Menu(self.menubar, tearoff=0)
        m.add_command(label="Nova", accelerator="Ctrl+N", command=self.new_file)
        m.add_command(label="Malfermi…", accelerator="Ctrl+O", command=self.open_dialog)
        m.add_command(label="Konservi", accelerator="Ctrl+S", command=self.save)
        m.add_command(label="Konservi kiel…", accelerator="Ctrl+Shift+S", command=self.save_as)
        m.add_separator()
        m.add_command(label="Eliri", command=self.quit)
        self.menubar.add_cascade(label="Dosiero", menu=m)

        m = tk.Menu(self.menubar, tearoff=0)
        m.add_command(label="Malfari", accelerator="Ctrl+Z", command=lambda: self._undo(False))
        m.add_command(label="Refari", accelerator="Ctrl+Y", command=lambda: self._undo(True))
        m.add_separator()
        m.add_command(label="Tondi", accelerator="Ctrl+X", command=lambda: self.text.event_generate("<<Cut>>"))
        m.add_command(label="Kopii", accelerator="Ctrl+C", command=lambda: self.text.event_generate("<<Copy>>"))
        m.add_command(label="Alglui", accelerator="Ctrl+V", command=lambda: self.text.event_generate("<<Paste>>"))
        m.add_command(label="Elekti ĉion", accelerator="Ctrl+A", command=self.select_all)
        m.add_separator()
        m.add_command(label="Serĉi kaj anstataŭigi…", accelerator="Ctrl+F", command=self.find_dialog)
        m.add_command(label="Iri al linio…", accelerator="Ctrl+G", command=self.goto_dialog)
        self.menubar.add_cascade(label="Redakti", menu=m)

        m = tk.Menu(self.menubar, tearoff=0)
        for label, tag, acc, _seq in TAG_MENU:
            m.add_command(label=label, accelerator=acc or "",
                          command=lambda t=tag: self.wrap_tag(t))
        self.menubar.add_cascade(label="Etikedoj", menu=m)

        m = tk.Menu(self.menubar, tearoff=0)
        m.add_checkbutton(label="cx → ĉ dum skribado (Retropaŝo malfaras)", variable=self.auto_cx,
                          command=self._update_status)
        m.add_checkbutton(label="Aŭtomata linifaldo", variable=self.wrap, command=self._toggle_wrap)
        m.add_checkbutton(label="Kolorigi etikedojn", variable=self.highlight_on, command=self._schedule_highlight)
        self.menubar.add_cascade(label="Opcioj", menu=m)

        self.plugin_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Kromprogramoj", menu=self.plugin_menu)

        m = tk.Menu(self.menubar, tearoff=0)
        m.add_command(label="Pri la programo…", command=self.about)
        self.menubar.add_cascade(label="Helpo", menu=m)

    # ---------------------------------------------------------------- plugin
    def load_plugins(self):
        self.plugins = []
        self.plugin_errors = []
        self.plugin_accels = {}          # etichetta -> scorciatoia mostrata nel menu
        self.plugin_hotkeys = []         # (sequenza Tk, funzione, etichetta)
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
                for act in actions:
                    label, func = act[0], act[1]
                    if len(act) > 2 and act[2]:
                        self.plugin_accels[label] = act[2]
                    self.plugins.append((category, label, func))
                for seq, func in getattr(mod, "HOTKEYS", {}).items():
                    self.plugin_hotkeys.append((seq, func, fn))
            except Exception as e:  # un plugin rotto non deve fermare l'editor
                self.plugin_errors.append((fn, e))

    def _build_plugin_menu(self):
        m = self.plugin_menu
        m.delete(0, "end")
        cats = {}
        for cat, label, func in self.plugins:
            cats.setdefault(cat, []).append((label, func))
        ordered = [c for c in CATEGORY_ORDER if c in cats] + \
                  sorted(c for c in cats if c not in CATEGORY_ORDER)
        for cat in ordered:
            sub = tk.Menu(m, tearoff=0)
            for label, func in cats[cat]:
                sub.add_command(label=label, accelerator=self.plugin_accels.get(label, ""),
                                command=lambda f=func, l=label: self.run_plugin(f, l))
            m.add_cascade(label=cat, menu=sub)
        for fn, err in self.plugin_errors:
            m.add_command(label=f"⚠ {fn}: eraro", command=lambda f=fn, e=err: show_error(
                self.root, f"Ne eblas ŝargi la kromprogramon {f}:\n\n{e}"))
        m.add_separator()
        m.add_command(label="Reŝargi kromprogramojn", command=self.reload_plugins)
        m.add_command(label="Malfermi la dosierujon de kromprogramoj", command=self.open_plugin_dir)

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
            show_error(self.root, f"Ne eblas malfermi la dosierujon:\n{PLUGIN_DIR}\n\n{e}")

    def about(self):
        show_info(self.root,
                  f"{APP_NAME} {VERSION}\n\n"
                  "UTF-8-redaktilo kun kromprogramoj por Esperanto kaj la teknikaj konvencioj de Monato.\n\n"
                  f"Dosierujo de kromprogramoj:\n{PLUGIN_DIR}\n\n"
                  "Nova kromprogramo = nova .py-dosiero en tiu dosierujo, poste "
                  "Kromprogramoj → Reŝargi kromprogramojn.\n\n"
                  "Licenco: vidu LICENCO.txt", title="Pri la programo")

    def reload_plugins(self):
        self.load_plugins()
        self._build_plugin_menu()
        self._bind_plugin_hotkeys()
        self.set_status_message(f"{len(self.plugins)} funkcioj de kromprogramoj ŝargitaj")

    def _bind_plugin_hotkeys(self):
        for w, seq in getattr(self, "_bound_hotkeys", []):
            try:
                w.unbind(seq)
            except tk.TclError:
                pass
        self._bound_hotkeys = []
        for seq, func, name in self.plugin_hotkeys:
            for w in (self.text, self.root):
                w.bind(seq, lambda e, f=func, n=name: (self.run_plugin(f, n), "break")[1])
                self._bound_hotkeys.append((w, seq))

    def run_plugin(self, func, label):
        try:
            func(self.ctx)
        except Exception:
            tb = traceback.format_exc()
            show_error(self.root, f"Eraro en la kromprogramo «{label}»:\n\n{tb[-1500:]}")
        self.text.focus_set()

    # --------------------------------------------------------------- tasti
    def _bind_keys(self):
        t = self.text

        def bind(seq, fn):
            for w in (t, self.root):
                w.bind(seq, lambda e, f=fn: (f(), "break")[1])

        bind("<Control-n>", self.new_file)
        bind("<Control-o>", self.open_dialog)
        bind("<Control-s>", self.save)
        bind("<Control-S>", self.save_as)
        bind("<Control-f>", self.find_dialog)
        bind("<Control-g>", self.goto_dialog)
        bind("<Control-a>", self.select_all)
        bind("<Control-y>", lambda: self._undo(True))
        for _label, tag, _acc, seq in TAG_MENU:
            if seq:
                bind(seq, lambda tg=tag: self.wrap_tag(tg))

        t.bind("<KeyPress-x>", self._on_x)
        t.bind("<KeyPress-X>", self._on_x)
        t.bind("<KeyPress-BackSpace>", self._on_backspace)
        t.bind("<Key>", self._on_any_key)

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
        self.text.configure(wrap="word" if self.wrap.get() else "none")
        self._redraw_gutter()

    # --------------------------------------------------------------- file
    def _confirm_discard(self):
        if not self.dirty:
            return True
        ans = yes_no_cancel(self.root, "La dokumento havas nekonservitajn ŝanĝojn.\nĈu konservi?")
        if ans is None:
            return False
        if ans:
            return self.save()
        return True

    def new_file(self):
        if not self._confirm_discard():
            return
        self._load("", None)

    def open_dialog(self):
        if not self._confirm_discard():
            return
        p = filedialog.askopenfilename(
            parent=self.root, title="Malfermi",
            filetypes=[("Tekstoj kaj Monato", "*.txt *.xml *.monato"), ("Ĉiuj dosieroj", "*.*")])
        if p:
            self._open_path(p)

    def open_file(self, path):
        self._open_path(path)

    def _open_path(self, path):
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as e:
            show_error(self.root, f"Ne eblas malfermi la dosieron:\n{e}")
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
        self.eol = "\r\n" if "\r\n" in s else "\n"
        s = s.replace("\r\n", "\n")
        self._load(s, path, note)

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
            parent=self.root, title="Konservi kiel", defaultextension=".xml",
            initialfile=os.path.basename(self.path) if self.path else "",
            filetypes=[("XML de Monato", "*.xml"), ("Teksto", "*.txt"), ("Ĉiuj dosieroj", "*.*")])
        if not p:
            return False
        return self._write(p)

    def _write(self, path):
        data = self.get_text().replace("\n", self.eol)
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(data)
        except OSError as e:
            show_error(self.root, f"Ne eblas konservi:\n{e}")
            return False
        self.path = path
        self.encoding_note = "UTF-8"
        self.dirty = False
        self._update_title()
        self._update_status()
        return True

    def quit(self):
        if self._confirm_discard():
            self.root.destroy()

    # -------------------------------------------------------- pannello report
    def show_report(self, title, items):
        self.report_list.delete(0, "end")
        self._report_lines = []
        for it in items:
            if isinstance(it, (tuple, list)):
                line, msg = it[0], it[1]
                self.report_list.insert("end", f"linio {line}: {msg}")
                self._report_lines.append(line)
            else:
                self.report_list.insert("end", str(it))
                self._report_lines.append(None)
        self.panel_title.config(text=title)
        self.panel.pack(side="bottom", fill="x", before=self.main)
        if self._report_lines:
            self.report_list.selection_set(0)
            self.report_list.activate(0)
        self._redraw_gutter()

    def hide_report(self):
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
        d.title("Serĉi kaj anstataŭigi")
        d.transient(self.root)
        d.resizable(False, False)
        self._fd = d
        self._find_var = tk.StringVar()
        self._repl_var = tk.StringVar()
        self._case_var = tk.BooleanVar(value=False)
        sel = self.get_selection()
        if sel and "\n" not in sel:
            self._find_var.set(sel)

        ttk.Label(d, text="Serĉi:").grid(row=0, column=0, padx=6, pady=4, sticky="e")
        e1 = ttk.Entry(d, textvariable=self._find_var, width=34)
        e1.grid(row=0, column=1, columnspan=3, padx=6, pady=4)
        ttk.Label(d, text="Anstataŭigi per:").grid(row=1, column=0, padx=6, pady=4, sticky="e")
        ttk.Entry(d, textvariable=self._repl_var, width=34).grid(row=1, column=1, columnspan=3, padx=6)
        ttk.Checkbutton(d, text="Distingi majusklojn", variable=self._case_var).grid(
            row=2, column=1, columnspan=3, sticky="w", padx=6)
        ttk.Button(d, text="Serĉi antaŭen", command=lambda: self.find_next(False)).grid(row=3, column=1, pady=6)
        ttk.Button(d, text="Serĉi malantaŭen", command=lambda: self.find_next(True)).grid(row=3, column=2)
        ttk.Button(d, text="Anstataŭigi", command=self.replace_one).grid(row=3, column=3, padx=2)
        ttk.Button(d, text="Anstataŭigi ĉion", command=self.replace_all).grid(row=4, column=3, padx=2, pady=(0, 8))
        e1.focus_set()
        e1.bind("<Return>", lambda e: self.find_next(False))
        d.bind("<Escape>", lambda e: d.destroy())

    def find_next(self, backwards=False):
        pat = self._find_var.get()
        if not pat:
            return False
        t = self.text
        if t.tag_ranges("sel"):
            start = t.index("sel.first") if backwards else t.index("sel.last")
        else:
            start = t.index("insert")
        idx = t.search(pat, start, backwards=backwards, nocase=not self._case_var.get())
        if not idx:
            self.set_status_message("Ne trovita")
            return False
        end = f"{idx}+{len(pat)}c"
        t.tag_remove("sel", "1.0", "end")
        t.tag_add("sel", idx, end)
        t.mark_set("insert", idx if backwards else end)
        t.see(idx)
        return True

    def replace_one(self):
        pat = self._find_var.get()
        sel = self.get_selection()
        if sel is not None and (sel == pat or (not self._case_var.get() and sel.lower() == pat.lower())):
            self.replace_selection(self._repl_var.get())
        self.find_next(False)

    def replace_all(self):
        pat = self._find_var.get()
        if not pat:
            return
        flags = 0 if self._case_var.get() else re.IGNORECASE
        repl = self._repl_var.get()
        new, n = re.subn(re.escape(pat), lambda m: repl, self.get_text(), flags=flags)
        if n:
            self.set_text(new)
        self.set_status_message(f"{n} anstataŭigoj")

    # ------------------------------------------------- evidenziazione / stato
    def _schedule_highlight(self):
        if self._hl_job:
            self.root.after_cancel(self._hl_job)
        self._hl_job = self.root.after(150, self._highlight)

    def _highlight(self):
        self._hl_job = None
        t = self.text
        for name in ("tag", "unknown", "comment"):
            t.tag_remove(name, "1.0", "end")
        if not self.highlight_on.get():
            return
        s = self.get_text()
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

    def _on_modified(self, _e=None):
        # <<Modified>> scatta solo quando il flag cambia: lo riazzeriamo
        # ogni volta e teniamo un nostro flag "dirty".
        if not self.text.edit_modified():
            return
        self.dirty = True
        self.text.edit_modified(False)
        self._schedule_highlight()
        self._update_title()
        self._update_status()
        self._redraw_gutter()

    def _on_cursor_move(self):
        self.text.tag_remove("hit", "1.0", "end")
        self._status_msg = ""
        self._update_status()

    def _on_yscroll(self, *a):
        self.vsb.set(*a)
        self._redraw_gutter()

    def _redraw_gutter(self):
        g = self.gutter
        g.delete("all")
        w = int(g.cget("width"))
        i = self.text.index("@0,0")
        last = None
        while True:
            d = self.text.dlineinfo(i)
            if d is None:
                break
            ln = i.split(".")[0]
            if ln != last:
                g.create_text(w - 6, d[1], anchor="ne", text=ln, font=self.font, fill="#888")
                last = ln
            nxt = self.text.index(f"{i}+1line")
            if nxt == i:
                break
            i = nxt

    def _update_title(self):
        name = os.path.basename(self.path) if self.path else "sennoma"
        mod = "*" if self.dirty else ""
        self.root.title(f"{mod}{name} — {APP_NAME}")

    def set_status_message(self, msg):
        self._status_msg = msg
        self._update_status()

    def _update_status(self):
        line, col = self.text.index("insert").split(".")
        n = len(self.get_text())
        parts = [f"Linio {line}, kol. {int(col) + 1}", f"{n} signoj", self.encoding_note,
                 "cx→ĉ: " + ("jes" if self.auto_cx.get() else "ne")]
        s = "   |   ".join(parts)
        if self._status_msg:
            s += "   |   " + self._status_msg
        self.status.config(text=s)


def main():
    root = tk.Tk()
    if "--proba" in sys.argv:                 # prova: carica i kromprogramoj, stampa e chiude
        app = App(root)
        print("FROZEN:", FROZEN, "| PLUGIN_DIR:", PLUGIN_DIR)
        for cat, label, _f in app.plugins:
            print("PLUGIN:", cat, "|", label)
        for fn, err in app.plugin_errors:
            print("ERARO:", fn, "->", err)
        root.destroy()
        return
    path = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
    App(root, path)
    root.mainloop()


if __name__ == "__main__":
    main()
