# Changelog

The most relevant changes in Redaktilo, in reverse chronological order.

## Unreleased

## 2.35 - 2026-11-16

- Security: replaced shell calls with subprocess in the plugin folder opener; XML parsing hardened with defusedxml; added the Security Audit workflow

## Released

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
- Version bumped to 2.33.

### Fixed
- Font and menu sizes did not follow the settings: only the editor text changed (#5).
- The help text of Search and replace was never translated, because the key in the code did not match the one in the language packs.

### Documentation
- Documented the language-pack format, placeholder rules, and how to add a language or plugin translations in `lingvoj/LEGUMIN.txt`.
