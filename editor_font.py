# -*- coding: utf-8 -*-
"""Avvio di Redaktilo con impostazioni personalizzabili per font e dimensione.

Avviare con: python editor_font.py [file ...]
Richiede le stesse dipendenze e cartelle del programma originale.
"""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

import editor


def _clamp_size(value, fallback=12):
    try:
        return max(8, min(48, int(value)))
    except (TypeError, ValueError):
        return fallback


def _patch_app():
    original_build_ui = editor.App._build_ui
    original_build_menus = editor.App._build_menus

    def build_ui(self):
        original_build_ui(self)
        settings = editor.load_settings()
        family = settings.get("editor_font_family", self.font.cget("family"))
        available = set(tkfont.families(self.root))
        if family not in available:
            family = self.font.cget("family")
        size = _clamp_size(settings.get("editor_font_size", self.font.cget("size")))
        self.font.configure(family=family, size=size)

    def set_editor_font(self, family, size):
        available = set(tkfont.families(self.root))
        if family not in available:
            return
        size = _clamp_size(size, self.font.cget("size"))
        self.font.configure(family=family, size=size)
        self.report_list.configure(font=self.font)
        for doc in self.docs:
            doc.text.configure(font=self.font)
            doc.text.tag_configure("comment", font=self._italic())
            self._redraw_gutter(doc)
        settings = editor.load_settings()
        settings["editor_font_family"] = family
        settings["editor_font_size"] = size
        try:
            editor.save_settings(settings)
        except OSError as exc:
            editor.show_error(self.root, editor.tr("Ne eblas konservi:\n{e}").format(e=exc))

    def font_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(editor.tr("Fonto"))
        dialog.transient(self.root)
        dialog.resizable(False, False)
        family = tk.StringVar(value=self.font.cget("family"))
        size = tk.StringVar(value=str(self.font.cget("size")))
        ttk.Label(dialog, text=editor.tr("Fonto:")).grid(row=0, column=0, padx=8, pady=8, sticky="e")
        families = sorted(set(tkfont.families(self.root)))
        fonts = ttk.Combobox(dialog, textvariable=family, values=families, state="readonly", width=30)
        fonts.grid(row=0, column=1, padx=8, pady=8)
        ttk.Label(dialog, text=editor.tr("Grando:")).grid(row=1, column=0, padx=8, pady=8, sticky="e")
        size_entry = ttk.Spinbox(dialog, textvariable=size, from_=8, to=48, width=8)
        size_entry.grid(row=1, column=1, padx=8, pady=8, sticky="w")

        def apply():
            self.set_editor_font(family.get(), size.get())
            dialog.destroy()

        buttons = ttk.Frame(dialog)
        buttons.grid(row=2, column=0, columnspan=2, pady=(0, 8))
        ttk.Button(buttons, text=editor.tr("Bone"), command=apply).pack(side="left", padx=4)
        ttk.Button(buttons, text=editor.tr("Nuligi"), command=dialog.destroy).pack(side="left", padx=4)
        dialog.bind("<Return>", lambda _event: apply())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.grab_set()
        fonts.focus_set()

    def build_menus(self):
        original_build_menus(self)
        menu_name = self.menubar.entrycget(editor.tr("Opcioj"), "menu")
        options = self.root.nametowidget(menu_name)
        options.add_separator()
        options.add_command(label=editor.tr("Fonto…"), command=self.font_dialog)

    editor.App._build_ui = build_ui
    editor.App._build_menus = build_menus
    editor.App.set_editor_font = set_editor_font
    editor.App.font_dialog = font_dialog


_patch_app()

if __name__ == "__main__":
    editor.main()
