# -*- coding: utf-8 -*-
"""Serĉas mankantajn komojn antaŭ ke, kiu, kiam..."""
import re
import monato_common as mc

CATEGORY = "Kontroliloj"
NAME = "Mankantaj komoj"

NON_SERVE = {"kaj", "aŭ"}

# Vortaro: vortaroj/vortaro_komoj.txt (kune kun la aliaj vortaroj, apud la programo)
VORTARO_PATH = mc.vortaro_path("vortaro_komoj.txt")


def leggi_vocabolario():
    with open(VORTARO_PATH, encoding="utf-8") as f:
        return tuple(
            parola.strip()
            for parola in f
            if parola.strip() and not parola.strip().startswith("#")
        )


def run(ctx):
    try:
        congiunzioni = leggi_vocabolario()
    except FileNotFoundError:
        ctx.error(f"Ne troviĝis la vortaro:\n{VORTARO_PATH}")
        return

    if not congiunzioni:
        ctx.info("La vortaro estas malplena.")
        return

    # Ordina le espressioni dalla più lunga alla più corta
    alternative = sorted(
        congiunzioni,
        key=len,
        reverse=True
    )

    alternative = [
        r"[^\S\n]+".join(re.escape(p) for p in voce.split())
        for voce in alternative
    ]

    # Cerca le espressioni del vocabolario
    pattern = re.compile(
        r"(?<!\w)("
        + "|".join(alternative)
        + r")(?!\w)",
        re.IGNORECASE
    )

    text = mc.blank_comments(ctx.text)
    text = re.sub(
        r"<[^>]*>",
        lambda m: " " * len(m.group(0)),
        text
    )

    lines = text.split("\n")
    items = []

    for n, line in enumerate(lines, start=1):
        matches = list(pattern.finditer(line))
        selezionate = []

        # Conserva soltanto le espressioni non contenute
        # in altre espressioni più lunghe
        for m in matches:
            inizio, fine = m.span()

            # Se prima dell'espressione c'è già una virgola,
            # non serve segnalare nulla
            prima = line[:inizio].rstrip()

            if prima.endswith(","):
                continue

            if any(
                inizio >= altra.start() and fine <= altra.end()
                for altra in selezionate
            ):
                continue

            selezionate = [
                altra for altra in selezionate
                if not (
                    altra.start() >= inizio
                    and altra.end() <= fine
                )
            ]

            selezionate.append(m)

        for m in selezionate:
            inizio = m.start()

            # Recupera la parola immediatamente precedente
            prima = line[:inizio].rstrip()
            precedente = re.search(r"(\w+)$", prima)

            if not precedente:
                continue

            parola = precedente.group(1)

            if parola.lower() in NON_SERVE:
                continue

            espressione = m.group(1)

            items.append((
                n,
                f"«{parola} {espressione}»  →  "
                f"«{parola}, {espressione}»"
            ))

    if not items:
        ctx.info("Neniu vortara esprimo trovita.")
        return

    ctx.report(
        f"Vortaraj esprimoj trovitaj: {len(items)}",
        items
    )
