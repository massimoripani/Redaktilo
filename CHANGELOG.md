# Changelog

The most relevant changes in Redaktilo, in reverse chronological order.

## Unreleased

## 2.35 - 2026-11-16

### Added
- Help → Technical conventions of Monato…: opens https://www.monato.be/red/tek_konv.php in the default browser (translated in all language packs).

### Security
- Plugin folder opener: replaced shell calls with `subprocess` (argument list, no shell), so the path can no longer inject commands.
- XML parsing in `htmlumilo.py` hardened with `defusedxml` (new dependency in `requirements.txt`).
- Fixed an inefficient regular expression (ReDoS) in `monato_common.py` that could freeze keyword extraction on specially crafted text.

### Development
- Added a Security Audit workflow on GitHub Actions (Bandit and Ruff security rules).

## 2.34 – 2026-11-15

### Added
- Global UI scaling from the new View → Scale menu, with values from 75% to 300% in 25% steps; changes apply immediately, without restarting, and are saved to `settings.json` (key `interfaca_skalo`).
- Keyboard shortcuts to change the scale: Increase scale (Ctrl+plus), Decrease scale (Ctrl+minus) and Normal scale (Ctrl+0). They can be customized from Key shortcuts… and also appear in the Scale submenu.
- Application-drawn, resizable menu bar; menus and dialogs follow the current interface scale. Dropdown menus and submenus, including plugin menus and context menus, use a scaled font.
- Plugin support for adapting custom pixel sizes to the current scale via `ctx.scale` and `ctx.sc(px)`.



### Changed
- User settings are saved to `settings.json` in Redaktilo's configuration directory.
- Interface scaling now resizes fonts, spacing, and widgets while keeping the user's chosen base font size unchanged; the scale is restored at startup. Saved scale values outside the allowed range go back to 100%.
- The Font…, Key shortcuts…, and Language entries were moved under the View menu, which now sits between Options and Plugins. Options only keeps the toggles (cx → ĉ while typing, automatic line wrapping, tag highlighting).
- With the application-drawn menu bar, the Alt key no longer opens the menus, and moving between menus takes one click.
- Language packs with supported languages: Esperanto, Italian, English, German, Spanish, French, Polish, Russian, and Ukrainian.
- Version bumped to 2.34.

### Fixed
- Font and menu sizes did not follow the settings: only the editor text changed (#5).
- The help text of Search and replace was never translated, because the key in the code did not match the one in the language packs.

### Documentation
- Documented the language-pack format, placeholder rules, and how to add a language or plugin translations in `lingvoj/LEGUMIN.txt`.

## 2.33 – 2026-11-14

### Added
- Esperanto hyphenation checker plugin, with tests (#2).
- Optional, customizable editor font: the font and size can be chosen and are saved (#4).

## 2.32 – 2026-11-13

First public release: a lightweight UTF-8 text editor with plugins, built for Esperanto writing and the technical conventions of the magazine Monato (XML articles). Ready-to-run Windows and Linux builds are provided.

### Added
- Multiple documents in tabs: each document has its own text, undo/redo history and plugin results. An already-open file just switches to its tab. Ctrl+W closes the tab, Ctrl+PgDn / Ctrl+PgUp switch tab.
- Customizable keyboard shortcuts for built-in commands and plugin functions, with conflict detection, saved per user (`klavkombinoj.json`).
- Language packs: interface in Esperanto, Italian and English; new languages are plain JSON files in `lingvoj/`, and plugins can ship their own translation files.
- Search and replace with regular expressions and special characters (`\n`, `\t`, `\uXXXX`, `\xHH`), with built-in help.
- Exportable plugin results: copy all or selected lines, or save as `.txt` / `.csv` (Excel-friendly).
- Plugins (`kromprogramoj/`):
  - Checks: tags and comments validator, missing-comma finder (ke, kiu, kiam…), character counter, interactive spell checker (F7).
  - Conversion: Text → Monato article, Text → Monato interview.
  - Text: cx ↔ ĉ, rebuild paragraphs, HTML entities → characters.
  - Tools: extract keywords → `<sv>`, HTML preview in the browser.
- Spell checker based on the Hunspell Esperanto dictionary via `spylls` (pure Python), with suggestions computed in the background and own words in `vortaroj/propra.txt`.
- Plugin API: `ctx.error()` and `ctx.tr()`; plugin messages and labels are translated when a matching key exists in the language pack. Plugins are loaded from `kromprogramoj/` at start-up and can be reloaded from the menu; a broken plugin is listed as an error instead of stopping the editor.
- Encoding: opens UTF-8, Windows-1252 and Latin-1; always saves UTF-8, keeping the original line endings.
- cx → ĉ typing aid (Backspace undoes the conversion).
- Windows build scripts `konstrui_exe.bat` / `konstrui_exe.sh` (PyInstaller).
