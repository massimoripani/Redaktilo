# Changelog

The most relevant changes in Redaktilo, in reverse chronological order.

## Unreleased

### Added
- Global UI scaling from the new View → Scale menu, with values from 75% to 300% in 25% steps; changes apply immediately and are saved to settings.
- Application-drawn, resizable menu bar; menus and dialogs follow the current interface scale.
- Plugin support for adapting custom pixel sizes to the current scale via `ctx.scale` and `ctx.sc(px)`.
- Search and replace with an option to operate across all open tabs; searching only the current tab remains available.
- Recent files menu with a persistent list and the ability to clear it.
- Interface language packs with supported languages: Esperanto, Italian, English, German, Spanish, French, Polish, Russian, and Ukrainian.
- Loading of additional plugin language packs, separated by language and plugin (for example `it.plugin_name.json`). Plugin strings without translation continue to be displayed in Esperanto.

### Changed
- User settings are saved to `settings.json` in Redaktilo's configuration directory.
- Interface scaling now resizes fonts, spacing, and widgets while keeping the user's chosen base font size unchanged; the scale is restored at startup.
- The Font…, Key shortcuts…, and Language entries were moved under the View menu.

### Documentation
- Documented the language-pack format, placeholder rules, and how to add a language or plugin translations in `lingvoj/LEGUMIN.txt`.
